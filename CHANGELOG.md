CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠します。  

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ基本情報
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定値をロードする自動読み込み機能。
    - プロジェクトルートを .git または pyproject.toml から探索するため、CWD に依存しない動作。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応。
    - .env のパースにおいて export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、行内コメント処理をサポート。
    - override フラグと protected キーセットにより OS 環境変数の上書きを保護。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定等をプロパティとして参照可能。
    - 必須環境変数未設定時は ValueError を発生させる明示的なチェック。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）のバリデーション。

- AI モジュール (kabusys.ai)
  - ニュースNLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントスコアを算出。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を実装し、DuckDB の UTC 時刻列と整合するよう設計。
    - バッチサイズ制御（最大 20 銘柄/回）、1 銘柄あたりの最大記事数・文字数制限、スコア ±1.0 のクリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、かつ非致命的失敗時はスキップして処理継続するフェイルセーフ設計。
    - API レスポンスの堅牢なバリデーション（JSON 抽出、results 配列の検証、既知コードのみ採用、数値チェック）。
    - 書き込みは冪等性を意識した DELETE → INSERT のトランザクション処理（DuckDB executemany の互換性考慮）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api をモック可能）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照し、calc_news_window を用いて記事ウィンドウを算出、OpenAI（gpt-4o-mini）へ送信して macro_sentiment を取得。
    - 再試行ロジック、API 失敗時は macro_sentiment=0.0 とするフォールバック、結果のクリップ化を実装。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、例外発生時は ROLLBACK）。

- データプラットフォーム関連 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー（market_calendar）管理機能を提供。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の判定 API を実装。
    - market_calendar が未取得時は曜日（平日）ベースでフォールバックする一貫した挙動。
    - next/prev_trading_day は DB の登録値を優先し、未登録日は曜日フォールバック。探索上限を設定して無限ループ回避。
    - 夜間バッチ calendar_update_job を実装し、J-Quants クライアント経由で差分取得→保存（バックフィル, sanity checks を含む）。
  - ETL パイプライン (kabusys.data.pipeline, etl)
    - ETLResult データクラスを公開し ETL の実行結果を集約（取得数・保存数・品質問題・エラー一覧など）。
    - 差分更新・バックフィル・品質チェック（quality モジュールとの連携）を設計に含む（実装インターフェースとユーティリティを提供）。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。
    - J-Quants クライアントを注入してテスト可能にする設計指向。
  - jquants_client のラッパー経由での市場データ取得・保存を想定した設計（詳細実装は jquants_client 側）。

- 研究・因子 (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200 日移動平均乖離率を計算。データ不足時は None を返す設計。
    - ボラティリティ／流動性 (calc_volatility): 20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比率を計算。
    - バリュー (calc_value): raw_financials から直近の EPS/ROE を結合して PER/ROE を算出。EPS が 0/欠損時は None。
    - DuckDB SQL を活用して効率よく集計・窓関数を使用。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算 (calc_forward_returns): 指定ホライズン（デフォルト [1,5,21]）の将来終値リターンを一度のクエリで取得。
    - IC 計算 (calc_ic): スピアマンのランク相関（ρ）をランク処理経由で計算。サンプル数不足時は None。
    - ランク関数 (rank): 同順位は平均ランクで処理（浮動小数誤差対策の丸め実装あり）。
    - 統計サマリー (factor_summary): 各カラムの count/mean/std/min/max/median を計算。
    - pandas 等の外部依存なしで純標準ライブラリ + DuckDB で動作。

Design / Implementation notes
- ルックアヘッドバイアス対策
  - datetime.today() / date.today() を各スコアリング/計算で直接参照せず、target_date を引数で受け取る設計。
  - DB クエリにおいても date < target_date のような排他条件を採用するなど、未来情報混入を防止する実装方針を明記。
- API 呼び出しの堅牢性
  - OpenAI 呼び出しは JSON Mode を利用し、レスポンスのパースに失敗した場合は安全側（スコア 0.0 やスキップ）で継続。
  - リトライは指数バックオフ、5xx と 429/ネットワーク系をリトライ対象に設定。非 5xx の API エラーは即スキップ。
- トランザクション安全性
  - DB への書き込みは BEGIN / DELETE / INSERT / COMMIT を用い、例外時は ROLLBACK を実行。ROLLBACK 自体の失敗は警告。
- テスト性の考慮
  - OpenAI への低レベル呼び出しは内部関数化して unittest.mock.patch による差し替えを想定。
  - 環境読み込みの自動化は KABUSYS_DISABLE_AUTO_ENV_LOAD によりテストで無効化可能。
- DuckDB 互換性向けの実装注記
  - executemany に空リストを渡すと失敗するバージョンがあるため、実行前に空チェックを行うなど互換性対応あり。

Known limitations / TODO
- Strategy / execution / monitoring パッケージ名は公開されているが、本リリースでは実行エンジンや実際の発注ロジック（kabu ステーションとの注文送信など）の実装は含まれていない（将来のリリースで追加予定）。
- 一部ファクター（PBR、配当利回りなど）は未実装（calc_value にて明記）。
- jquants_client, quality, および外部 API クライアントの具体的実装と設定例は別途ドキュメント参照が必要。

Security
- OpenAI や Slack 等のシークレットは環境変数経由で注入する設計。必須のキー未設定時は明示的に ValueError を発生させるため、誤った静的設定による意図しない公開を抑止。

---

この CHANGELOG は、ソースコードから確認できる実装と設計方針に基づき作成しています。必要であれば、各モジュールの変更点をさらに細分化して追記できます。