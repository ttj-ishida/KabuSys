CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠します。
リリース日付は本ファイル生成日 (2026-03-29) を用いています。

[0.1.0] - 2026-03-29
-------------------

Added
- 初回リリース。
- パッケージ公開:
  - kabusys.__init__ によりパッケージトップで data / strategy / execution / monitoring を公開。
  - バージョン: 0.1.0
- 環境設定管理 (kabusys.config):
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git / pyproject.toml を基準に検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - .env パーサ実装: export 形式のサポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理。
  - ファイル読み込み失敗時の警告出力。
  - Settings クラスで各種必須/任意設定をプロパティとして公開（J-Quants / kabu API / Slack / DB パス / 環境判定 / ログレベル等）。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の有効値チェック）と便宜メソッド（is_live, is_paper, is_dev）。
- AI 関連 (kabusys.ai):
  - news_nlp.score_news:
    - raw_news / news_symbols を集約して銘柄別にニュースを結合し、OpenAI（gpt-4o-mini）にバッチ送信してセンチメントを算出、ai_scores テーブルへ書き込み。
    - 時間ウィンドウ: JST ベースで前日 15:00 ～ 当日 08:30（UTC に変換して DB 比較）。
    - バッチ処理（銘柄ごとに最大 20 件）、1 銘柄あたり記事数/文字数上限でトリム。
    - JSON Mode を期待したレスポンスパース→不正な場合は最外側の {} を抽出して復元試行。
    - レスポンス検証（results 配列、code/score の型チェック、未知 code の無視、数値検証、±1.0 にクリップ）。
    - 429/接続断/タイムアウト/5xx に対する指数バックオフでのリトライ、その他はスキップして継続（フェイルセーフ）。
    - 部分成功に備え、書き込みは対象コードのみ削除→挿入する方式を採用（DuckDB 互換性考慮）。
    - テスト可能性のため OpenAI 呼び出し箇所を差し替え可能に実装。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - maco キーワードによる記事抽出、LLM 呼び出しのリトライ/フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - ルックアヘッドバイアスを避けるため target_date 未満のデータのみを参照し、datetime.today() を参照しない設計。
    - OpenAI 呼び出しは news_nlp と分離して独自実装（モジュール結合を避ける）。
- Data / ETL (kabusys.data):
  - pipeline.ETLResult を公開（kabusys.data.etl に再エクスポート）。
  - data.pipeline:
    - ETLResult データクラス（取得件数、保存件数、品質検査結果、エラー集計、ユーティリティメソッド）。
    - 差分取得／バックフィル／品質チェックに関する設計方針とユーティリティ関数（テーブル存在チェック、最大日付取得など）。
  - calendar_management:
    - JPX カレンダー管理 API 連携（jquants_client 経由）の夜間バッチ（calendar_update_job）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティ。
    - market_calendar がない場合の曜日ベースフォールバック、DB 登録値優先の一貫した動作、最大探索日数制限（_MAX_SEARCH_DAYS）やバックフィル・健全性チェック。
- Research (kabusys.research):
  - factor_research:
    - calc_momentum / calc_volatility / calc_value: DuckDB を用いたファクター算出（mom 1m/3m/6m、ma200乖離、ATR20、平均売買代金、volume ratio、PER/ROE）。
    - SQL ベースで営業日窓や欠損伝播を考慮した実装。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターン一括取得（入力検証あり）。
    - calc_ic: スピアマンのランク相関（IC）計算（結合、None/有限値除外、最小サンプルチェック）。
    - rank: 同順位は平均ランクで処理（丸めにより ties を安定検出）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）。
  - research パッケージで各種ユーティリティを再エクスポート。

Fixed / Notable implementation details
- DuckDB 互換性:
  - executemany に空リストを渡せないケース（DuckDB 0.10）を回避するため、書き込み前に params の空チェックを実装。
  - 日付型取り扱いの互換性を考慮して date 変換ユーティリティを用意。
- LLM 呼び出し・パースの堅牢化:
  - JSON モードでも稀に前後テキストが混ざるケースに備えた復元処理。
  - APIError の status_code の有無に依存せず安全に扱う実装（getattr を使用）。
  - 再試行ポリシーを明確化（リトライ対象の例外分類と指数バックオフ）。
- 安全性・使いやすさ:
  - 環境変数未設定時は明示的な ValueError を返す _require を採用し、早期に設定ミスを検出。
  - .env ロード時に OS 環境変数を保護（protected set）して上書きを制御可能。

Documentation / Design notes
- 多くのアルゴリズムは「ルックアヘッドバイアス防止」の方針に従い、内部で datetime.today()/date.today() を参照せず、呼び出し側から target_date を注入する設計。
- 外部 API（OpenAI / J-Quants）呼び出しはフェイルセーフを意識し、API 例外発生時でも全体処理を停止させない設計（ログ出力・部分スキップ／フォールバック値採用）。
- テストのために外部呼び出しポイント（_call_openai_api 等）を patch 可能にしている。

Unreleased
- （今後の変更点はこのセクションに記載します）