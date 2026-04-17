# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

（現状なし）

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 基本アプリケーション初期実装を追加。
  - パッケージメタ情報 (src/kabusys/__init__.py) にバージョン "0.1.0" を設定。
- 実行用エントリポイントを追加。
  - run_execution.py：ExecutionEngine 起動スクリプトを実装。KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading DB を使用し MockBroker を利用するなど、本番とペーパートレードを分離。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを実装。環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を参照する仕様。
- 設定・環境変数管理を実装（src/kabusys/config.py）。
  - プロジェクトルート自動検出 (.git / pyproject.toml) による .env の自動読み込み（.env と .env.local の優先順位と上書き制御）。
  - .env の行パーサを実装し、export 形式やクォート、インラインコメントなどに対応。
  - 各種設定プロパティ（DB パス、PID/kill フラグパス、閾値、環境種別チェック、paper_trading 用設定など）を提供。
  - `PAPER_FILL_MODE` の検証、`KABUSYS_ENV` / `LOG_LEVEL` のバリデーションを実装。
- ポートフォリオ構築関連の純粋関数群を追加（src/kabusys/portfolio）。
  - portfolio_builder: 候補選定（select_candidates）、等ウェイト/スコア加重（calc_equal_weights / calc_score_weights）。
  - risk_adjustment: セクター上限の適用（apply_sector_cap）、市場レジームに応じた乗数計算（calc_regime_multiplier）。
  - position_sizing: 発注株数算出ロジック（calc_position_sizes）を実装。risk_based / equal / score の割当方式、単元株丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した安全弁などを含む。
- 監視・実行補助ユーティリティを追加（src/kabusys/utils/process_priority.py）。
  - Windows と POSIX（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を提供。アクセス権や未対応 OS で安全にフォールバックする実装。
- リサーチ / ファクター計算機能を追加（src/kabusys/research）。
  - factor_research: Momentum / Volatility / Value の計算関数（calc_momentum, calc_volatility, calc_value）。DuckDB の prices_daily / raw_financials を使用する SQL ベース実装。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク化ユーティリティ（rank）。
  - DuckDB 接続を受ける設計で、外部 API に依存しない純粋なデータ処理を実現。
- AI ニュース NLP スコアリング機能を追加（src/kabusys/ai/news_nlp.py）。
  - raw_news から銘柄単位に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出、ai_scores テーブルへ書き込む処理フローを実装（バッチ化、トークン肥大防止、スコアクリップ、エラーハンドリング等）。
  - ニュースウィンドウ計算ユーティリティ（calc_news_window）を提供。
- 検証用ツールを追加（src/kabusys/tools/paper_verification_report.py）。
  - Paper Trading 用検証レポート生成スクリプトを実装。稼働率、注文成功率、送信率、レイテンシ（P95）などの指標を計算して PASS/FAIL 判定を行い CLI で出力可能。
  - P95 計算や期間フィルタ、DB 存在チェック、CLI 引数（--from/--to/--db）を実装。

### 変更 (Changed)
- なし（初回リリースのため既存変更なし）。

### 修正 (Fixed)
- 設計上の堅牢性向上を実施。
  - run_monitoring のポーリング間隔取得で不正な環境変数値に対してデフォルトへフォールバックし、ログ出力で通知するようにした（負値や非整数に対応）。
  - .env 読み込みでファイルオープン失敗時に警告を出し続行するようにした（テストや権限不足に対する耐性）。
  - process_priority / set_cpu_affinity は権限不足や未実装 API 呼出時に警告を出してスキップする実装で、クラッシュしないようにした。
  - portfolio の重み付け・株数計算でデータ欠損（価格未取得）の場合はスキップしてログを残すように調整。
  - research モジュールの SQL クエリはデータ不足時に None を返す等、欠損耐性を考慮。

### セキュリティ (Security)
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）で供給する方式を採用。未設定時は明示的なエラーを出す実装により誤った公開を避ける。

### 既知の制限 / 注意点 (Known Issues / Notes)
- ai/news_nlp.py は外部 API（OpenAI）への呼び出しを含むため、API 利用制限・課金・キー管理に注意が必要。
- run_monitoring は常に本番 sqlite_path を参照する設計（監視 DB は環境に依存しない）。この仕様は監視の一貫性を保つための意図的な設計である点に注意。
- calc_position_sizes は単元株（lot_size）を全銘柄共通としている。将来的に銘柄別 lot_size を導入する余地がある（TODO コメントあり）。
- research の計算は DuckDB 上のテーブル構造（prices_daily, raw_financials 等）に依存する。スキーマの不整合があると例外が発生する可能性がある。

---

## 参考: 今後の予定（例）
- 銘柄別 lot_size サポート、より細かいコスト見積り（手数料・スリッページ）対応。
- ai/news_nlp の部分失敗時のロールバック戦略や部分更新ポリシーの強化。
- テストカバレッジ拡充（特に DuckDB クエリと OpenAI 関連のフェイルケース）。