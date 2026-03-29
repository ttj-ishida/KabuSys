# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録します。  
このファイルはコードベース（src/kabusys 配下）の現状から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。日本株自動売買／リサーチプラットフォームのコア機能を実装しました。

### Added
- パッケージ基盤
  - パッケージのバージョンを `0.1.0` として設定（src/kabusys/__init__.py）。
  - パッケージ公開インターフェース（data, strategy, execution, monitoring）を定義。

- 設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機構（プロジェクトルート検出：.git または pyproject.toml を基準）。
  - `.env` / `.env.local` の読み込み優先順位（OS 環境変数 > .env.local > .env）、および `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化。
  - .env のパースで以下に対応：
    - コメント行・空行の無視
    - `export KEY=val` 形式のサポート
    - シングル／ダブルクォート内でのバックスラッシュエスケープ処理
    - クォートなし値のインラインコメント扱い（直前が空白/タブの場合のみ）
  - 必須変数チェック（_require）と値検証（KABUSYS_ENV, LOG_LEVEL 等）。
  - 主要な環境変数のアクセス用プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN など）。
  - デフォルト DB パス（duckdb, sqlite）の設定サポート。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（news_nlp.py）
    - raw_news と news_symbols からニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ。
    - チャンク処理（最大 20 銘柄／コール）、1銘柄あたりの最大記事数・文字数トリム。
    - JSON Mode での API 呼び出し、レスポンス検証（results 配列、code/score の検証）、スコア ±1 クリップ。
    - 429/ネットワーク断/タイムアウト/5xx 対応の指数バックオフリトライ。失敗時は該当チャンクをスキップ（フェイルセーフ）。
    - DuckDB へ書き込むときの冪等処理（DELETE → INSERT、部分失敗時に他銘柄を保護）。
    - テスト容易性のため _call_openai_api を patch 可能。
  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、ニュースベースの LLM マクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照し、ma200_ratio を算出・マクロ記事抽出・LLM 評価・スコア合成を行い、market_regime テーブルへ冪等書き込み。
    - LLM 呼び出しに対するリトライ（429/ネットワーク断/タイムアウト/5xx）とフォールバック（API 失敗時 macro_sentiment=0.0）。
    - lookahead バイアス回避（date 比較は target_date 未満等の排他条件、datetime.today() を直接参照しない）。
    - _call_openai_api は news_nlp と独立実装（モジュール結合を避ける）。

- データプラットフォーム（src/kabusys/data）
  - ETL 基盤（pipeline.py, etl.py）
    - ETLResult データクラス（取得数・保存数・品質問題・エラー一覧とユーティリティ）を実装。
    - 差分更新・バックフィル・品質チェック設計（J-Quants からの差分取得 → 保存 → quality チェック）。
    - DuckDB 上での最大日付取得やテーブル存在チェックユーティリティ。
    - ETL の設計方針として id_token 注入や部分失敗時の保護等を採用。
  - カレンダー管理（calendar_management.py）
    - market_calendar テーブルを元にした営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB の存在/未登録日について曜日ベース（土日除外）でのフォールバック。
    - 夜間バッチ更新ジョブ（calendar_update_job）: J-Quants から差分取得 → save_market_calendar による冪等保存、バックフィル・健全性チェック（将来日付の異常検出）。
    - 最大探索日数やバックフィル日数などの安全パラメータを導入（無限ループ防止等）。
  - jquants クライアント（モジュール参照のみ。実装は外部想定）への統合ポイントを確保。

- リサーチ（src/kabusys/research）
  - factor_research.py：ファクター計算（momentum, volatility, value）
    - モメンタム：1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。
    - ボラティリティ / 流動性：20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - バリュー：PER（EPS が 0 または欠損時は None）、ROE（最新の raw_financials を参照）。
    - DuckDB を用いた SQL ベースの実装（外部 API を呼ばない、結果は dict リストで返却）。
  - feature_exploration.py：探索用ユーティリティ
    - 将来リターン計算（calc_forward_returns）：指定ホライズンのリターンを一度に算出（LEAD を使用）。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関を実装（ties の平均ランク対応）。
    - ランク変換ユーティリティ（rank）：同順位は平均ランク、丸めで ties 検出漏れを低減。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を計算。
  - data.stats から zscore_normalize を re-export（研究ワークフロー統合）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

### Notes / 開発者向けメモ
- 設計上の重要な方針：
  - ルックアヘッドバイアスを避けるため、内部ロジックは datetime.today() / date.today() を直接参照しない（target_date を明示的に渡す設計）。
  - 外部 API（OpenAI, J-Quants）呼び出しは堅牢化（リトライ・バックオフ・部分失敗時の保護）を重視。
  - DB 書き込みは冪等化（DELETE → INSERT / ON CONFLICT）やトランザクション（BEGIN/COMMIT/ROLLBACK）で整合性を保つ。ROLLBACK の失敗は警告ログで 報告する。
  - DuckDB のバージョン差異（executemany の空リスト扱い等）を考慮した実装上の注意点がある（空パラメータ時は呼ばないガードを実装）。
  - テスト可能性を重視し、OpenAI 呼び出し箇所は patch しやすい形で分離している。

### Upgrade / Migration Notes
- 環境変数の必須項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY）は起動前に設定してください。設定がないと Settings のプロパティや AI スコアリング関数が ValueError を投げます。
- 自動 .env ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

---

（この CHANGELOG は現行ソースから推測して作成しています。実際のリリース履歴や日付は適宜調整してください。）