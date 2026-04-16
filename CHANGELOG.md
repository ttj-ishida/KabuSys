# CHANGELOG

すべての重要な変更を記録します。形式は "Keep a Changelog" に準拠しています。  
（以下は与えられたコードベースの内容から推測して作成した変更履歴です。）

## [Unreleased]

## [0.1.0] - 2026-04-16

Added
- 初期リリース: KabuSys 自動売買フレームワークの基礎機能を追加。
  - 実行・監視
    - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
      - 本番／Paper Trading の分離（Paper Trading 時は専用 SQLite DB を使用）。
      - BrokerClientFactory 経由でブローカークライアントを作成。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを起動。
      - 停止フラグ（data/stop_requested.flag）と PID ファイルによるプロセス管理、スレッドでの実行制御。
    - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に依らず本番 sqlite_path を使用して監視テーブルを初期化。
      - 停止フラグによる優雅な終了、例外ハンドリングを備えたポーリングループ。
  - 設定管理
    - 環境変数/.env ローダー（src/kabusys/config.py）
      - プロジェクトルート自動検出（.git または pyproject.toml を探索）。
      - .env/.env.local の自動ロードと OS 環境変数保護（上書き禁止）の仕組み。
      - 行パーサーはコメント、クォート、export 形式等に対応。
      - 各種設定プロパティ（DB パス、PAPER_FILL_MODE、KABUSYS_ENV/LOG_LEVEL 検証、監視閾値 等）。
  - ポートフォリオ構築
    - 銘柄選定と配分（src/kabusys/portfolio/portfolio_builder.py）
      - 候補選定（スコア降順＋タイブレーク）、等金額配分、スコア加重配分（全スコアが 0 の場合は等配分へフォールバック）。
    - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
      - セクター上限の適用（既存保有の時価ベースで判定、"unknown" セクターは制限対象外）。
      - レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
    - 株数決定・投下キャップ（src/kabusys/portfolio/position_sizing.py）
      - risk_based / equal / score の配分方式に対応。
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash に応じたスケールダウン）、cost_buffer を用いた保守的見積り。
      - スケールダウン時の残差処理（lot_size 単位で優先度付けして追加配分）。
  - 研究・ファクター計算
    - ファクター計算モジュール（src/kabusys/research/factor_research.py）
      - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（ATR20、相対ATR、出来高指標）、バリュー（PER, ROE）の計算。
      - DuckDB を使った SQL ベースのスライディングウィンドウ集計、データ不足時は None を返す仕様。
    - 特徴量探索（src/kabusys/research/feature_exploration.py）
      - 将来リターン（任意ホライズン）の計算、Spearman ランク相関（IC）計算、ファクター統計サマリ。
      - tie（同値）の扱いを安定させるランク計算ロジックを実装。
    - research パッケージの公開 API を整備（src/kabusys/research/__init__.py）。
  - ニュース NLP（AI）
    - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
      - raw_news / news_symbols から記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのスコアを生成し ai_scores テーブルに書き込む。
      - タイムウィンドウ計算（JST ベース → UTC 変換）、記事数/文字数のクリッピング、バッチ処理、レスポンス検証、スコアクリップ（±1.0）、リトライ（指数バックオフ）等の堅牢なフロー。
      - API キーは引数または環境変数から解決。ルックアヘッドバイアス回避の設計方針あり。
  - ツール
    - Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）
      - 稼働率、注文成功率、送信率、レイテンシ（P95）などを算出して PASS/FAIL 判定を出力。
      - DB 存在チェック、クエリ失敗時のフォールバック、コマンドライン引数（--from/--to/--db）対応。
  - ユーティリティ
    - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
      - Windows / POSIX（Linux, macOS, FreeBSD）双方を吸収する API。権限不足等のケースを警告でスキップ。
    - パッケージメタ（version=0.1.0）（src/kabusys/__init__.py）

Changed
- （初回リリースのため該当なし）

Fixed
- 環境変数ロードとパーサーの強化（src/kabusys/config.py）
  - export 形式・クォート内のエスケープ・コメント扱い等を考慮した堅牢な行パースを実装。
  - プロジェクトルートが特定できない場合は自動ロードをスキップする安全策を追加。
- ポートフォリオ・ポジションサイズの丸め・スケーリング処理を安全に実装（小数切り捨てや lot_size 単位の調整、残余配分の安定性向上）。

Security
- OpenAI API キーは明示的に引数か環境変数で提供する必要があり、未設定時はエラーを返す設計（src/kabusys/ai/news_nlp.py）。

Notes / Known limitations
- 一部関数で将来的な拡張（銘柄ごとの lot_size マスタ反映、価格フォールバック）が TODO コメントとして残されている。
- news_nlp の最後のフェーズでの処理（記事取得関数等）はスニペットが途中で切れているため、完全実装を要する箇所がある可能性がある（与えられたコードからの推測）。
- DuckDB / SQLite のスキーマやテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, system_status, trade_logs, risk_logs 等）は本 CHANGELOG 作成時点ではコード参照により想定されているが、実際のスキーマは別途管理される想定。

---

翻訳・注釈や追加情報が必要であればお知らせください。必要に応じてリリースノートをさらに細分化（ファイル単位の変更一覧やレビューチェックリスト追加）できます。