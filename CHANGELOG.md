Keep a Changelog 準拠 — 変更履歴 (日本語)
=================================

すべての変更点はセマンティックバージョニングに基づいて記載しています。
この CHANGELOG は初期リリース v0.1.0 をコードベースから推測して作成しています。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ基盤
  - パッケージ初期化: kabusys/__init__.py により主要サブパッケージ（data, research, ai, ...）を公開。
  - バージョン: __version__ = "0.1.0" を設定。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準にルートを探索（CWD に依存しない）。
    - 自動ロード無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で制御可能。
    - 読み込み優先順位: OS 環境変数 > .env.local (> override) > .env。
  - .env パーサを実装（kabusys.config._parse_env_line）
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ対応、インラインコメントの扱い（クォート有無で挙動差）。
  - 安全な読み込み: ファイル読み込み失敗時に警告を出す実装。
  - Settings クラスを公開 (settings)
    - J-Quants / kabuステーション / Slack / DB パスなどのプロパティを提供。
    - 値検証（env, log_level の許容値チェック）と便宜メソッド（is_live, is_paper, is_dev）。

- AI モジュール (kabusys.ai)
  - ニュースNLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄毎に記事を集約して OpenAI にバッチ送信し、銘柄ごとのセンチメント（ai_scores）を書き込む機能を実装。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換）を対象にする calc_news_window を提供。
    - バッチング: 最大 _BATCH_SIZE（20）銘柄ずつ処理、1銘柄あたり _MAX_ARTICLES_PER_STOCK（10）件 / _MAX_CHARS_PER_STOCK（3000文字）でトリム。
    - OpenAI JSON Mode を利用し厳密な JSON を期待。レスポンスの妥当性検証と数値型変換、 ±1.0 にクリップ。
    - エラーハンドリング: レート制限(429)、接続断、タイムアウト、5xx に対して指数バックオフでリトライ。非リトライ系は安全にスキップし続行（フェイルセーフ）。
    - DuckDB への書き込みは冪等性を考慮（該当コードのみ DELETE → INSERT）し、executemany の空リスト問題への対策あり。
    - テストフック: 内部で OpenAI 呼び出しを行う _call_openai_api をパッチで置換可能に実装。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算（ルックアヘッドを防止するため target_date 未満のデータのみ使用）。データ不足時は中立（1.0）にフォールバックし WARNING を出力。
    - マクロニュース取得: news_nlp.calc_news_window を利用してマクロキーワードでフィルタしたタイトルを取得し、OpenAI に送信して macro_sentiment を取得。記事が無い場合は LLM 呼び出しを行わず 0.0 とする。
    - OpenAI 呼び出しは retry/バックオフを実装。API 失敗時は macro_sentiment=0.0 で継続するフェイルセーフ。
    - レジームスコア合成後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。

- データ基盤 (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）の夜間バッチ更新ジョブ calendar_update_job を実装。J-Quants API から差分取得し保存、バックフィルや健全性チェックを実施。
    - 営業日判定とユーティリティ関数を提供: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB 登録が無い場合は曜日ベースのフォールバック（週末は非営業日）を用い、一貫した挙動を保証。
    - 最大探索日数の制限 (_MAX_SEARCH_DAYS) で無限ループを防止。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）。
    - 差分更新・保存・品質チェックを行うためのユーティリティ実装（J-Quants クライアント統合を想定）。
    - テーブル存在チェック、最大日付取得などのユーティリティを実装。
    - 設計として backfill（デフォルト 3 日）や calendar lookahead（90 日）などをサポートし、品質チェック結果を収集して上位で判断可能にする。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュール
    - Momentum: calc_momentum（1M/3M/6M リターン、200 日 MA 乖離）
    - Volatility: calc_volatility（20日 ATR、ATR 比、20日平均売買代金、出来高比率）
    - Value: calc_value（PER、ROE を raw_financials から取得して計算）
    - 上記は DuckDB の SQL ウィンドウ関数を活用し、データ不足は None を返す設計。
  - feature_exploration モジュール
    - 将来リターン: calc_forward_returns（任意ホライズンの fwd リターンを一括 SQL で取得）
    - IC（Information Coefficient）計算: calc_ic（Spearman ランク相関）
    - ランク化ユーティリティ: rank（同順位は平均ランク）
    - 統計サマリ: factor_summary（count/mean/std/min/max/median）

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- OpenAI API キーは直接引数で注入可能（api_key 引数）か環境変数 OPENAI_API_KEY を利用する。明示的な未設定チェックと ValueError を行うため、ミスコンフィグ時に早期に検出可能。

Notes / 実装上の注意点（ドキュメント相当）
- ルックアヘッドバイアス防止: 各種処理で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に与える）。
- テスト容易性: OpenAI 呼び出し部分は内部関数をモック可能にしており、API 呼び出しを差し替えて単体テストが行える。
- DuckDB 互換性: executemany の空リスト回避など、DuckDB の既知の制約に配慮した実装。
- フォールバック設計: API 失敗時は処理を継続しつつ、該当箇所は既定値（例: macro_sentiment=0）にフォールバックして安全に済ませる（フェイルセーフ）。

依存関係（コードから推測）
- duckdb
- openai

既知の未実装 / TODO（コードから推測）
- factor_research の一部指標（PBR・配当利回り）は未実装（コメント記載あり）。
- data.jquants_client の実装詳細や quality モジュールの具体的チェック項目は本 CHANGELOG には含まれない（別モジュールに委譲）。

---
この CHANGELOG は提供されたソースコード内容に基づき推測して作成されています。追加のコミット履歴や実際のリリースノートが存在する場合は、そちらに合わせて更新してください。