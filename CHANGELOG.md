CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
日付や内容はコードベースから推測して記載しています。

Unreleased
----------

- （今後のリリース向けのエントリをここに追加してください）


0.1.0 - 2026-04-16
-----------------

Added
- 基本アーキテクチャと起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクトの data/stop_requested.flag ファイルで制御。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。Paper Trading 環境では専用の MockBrokerClient と paper_trading DB を使用するよう分離。エンジンの PID 管理と停止フラグ検知を実装。

- 環境設定（Settings）モジュールを追加（kabusys.config）
  - .env 自動読み込み機能を備え、プロジェクトルート探索（.git または pyproject.toml 基準）により CWD に依存しない自動ロードを実現。
  - .env パーサは export 形式、クォート付き値、インラインコメント等に対応。OS 環境変数を保護する protected 上書き制御機能を実装。
  - 各種設定プロパティを提供（DB パス、Paper Trading 用パス、PID/kill フラグパス、各種閾値、ログレベル、環境種別判定等）と入力値検証（例: KABUSYS_ENV, PAPER_FILL_MODE, LOG_LEVEL のバリデーション）。

- ポートフォリオ構築ユーティリティ（kabusys.portfolio）
  - portfolio_builder: 候補選定（スコア順／タイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等金額にフォールバック）。
  - risk_adjustment: セクター集中のキャップ適用（既存保有を考慮）、市場レジームに応じた投下資金乗数の算出（bull/neutral/bear 対応、未知レジームはフォールバック）。
  - position_sizing: 発注株数計算（risk_based / equal / score の allocation_method 対応）、単元株（lot）丸め、aggregate cap によるスケールダウン、手数料・スリッページ用の cost_buffer を考慮した安全弁実装。将来の拡張向けに TODO を明記（銘柄別 lot_size など）。

- リサーチ / ファクター計算機能（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M・MA200 乖離）、ボラティリティ（20日 ATR・ATR%・20日平均売買代金・出来高比率）、バリュー（PER・ROE）などを DuckDB を使って計算する関数を追加。価格や財務の欠損に対する安全処理とウィンドウスキャンのバッファを設計。
  - feature_exploration: 将来リターン（複数ホライズン対応）、IC（Spearman のランク相関）、ファクター統計サマリー、ランク付けユーティリティを追加。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージの __all__ を整備して主要関数を公開。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を銘柄別に集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出する処理骨格を追加。
  - タイムウィンドウ計算（JST ベース→UTC 変換）、バッチサイズ制御、記事文字数／件数制限、API キー解決、429/ネットワーク/5xx に対する指数バックオフの考慮、結果バリデーション・スコアクリッピング、部分成功時のテーブル更新方針（対象コードのみを置換）を設計。API 呼び出し周りの再試行回数や待機時間の定数化も実施。

- 運用ツール（kabusys.tools）
  - paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定を出力。閾値（稼働率99%、注文成功率90% 等）と日付フィルタ、DB パスの引数オーバーライドをサポート。
  - tools パッケージを整備し CLI 実行可能に。

- プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - Windows と POSIX（Linux/macOS/FreeBSD）差分を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority を追加。権限不足や未対応 API を考慮して安全にフォールバック。
  - set_cpu_affinity により最初 N コアにプロセスをピン留めする機能を追加。入力検証と権限エラーハンドリングを実装。

- DB 周り
  - duckdb と sqlite3 を組み合わせて使用する設計を採用。監視テーブルの初期化関数（init_monitoring_db）を run_* スクリプトで呼び、冪等にテーブル存在を保証。

Changed
- Paper Trading と本番のデータ分離を明確化
  - run_execution では settings.is_paper に応じて paper_sqlite_path を使用するように設計。Paper Trading 系処理が本番 DB と完全分離されるようになった。

- 環境変数ロードの優先度・保護を明確化
  - OS 環境変数を保護しつつ .env.local での上書きが可能な自動ロード順序を採用。自動ロード自体は KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

Fixed
- 環境変数パースに関する細かいバグ回避
  - export プレフィックス、クォート付き値、インラインコメントやバックスラッシュエスケープの取り扱いを改善して .env の柔軟性を向上。

- いくつかの数値/ゼロ除算リスクに対する安全策を追加
  - factor/value, position sizing, volatility 等の関数でデータ欠損時に None を返す、または計算をスキップするようにして例外を抑制。

Known issues / Notes
- kabusys.ai.news_nlp モジュールは記事取得・バッチ送信以降の処理が設計されているが、スニペット末尾で途中（fetch_articles 呼び出し直後）で切れているため、fetch_articles 実装や最終的な書き込み処理が不足している可能性があります。実運用する場合は完全実装の確認が必要です。
- position_sizing 内に将来的な拡張（銘柄別 lot_size など）に関する TODO が残っています。
- run_monitoring は説明にある通り KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様になっています。Paper Trading の監視データを意図的に分離したい場合は仕様の見直しが必要です。
- DuckDB の executemany に関する制約（空 params の扱い）への注意をコメントで残しています。実装者は空配列での書き込みを避けること。

Security
- API キー等の必須値は Settings 経由で _require() により未設定時に明示的に例外を投げる仕様。環境変数の自動ロードは開発時の利便性を優先しつつ、KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト等で無効化可能。

メンテナ向け補足
- パッケージバージョンは kabusys.__version__ = "0.1.0" を設定済み。
- 起動スクリプトは直接 python -m での実行を想定（if __name__ == "__main__": main() を実装）。
- ログレベルや閾値は Settings 経由で環境変数により調整可能。

（以上）