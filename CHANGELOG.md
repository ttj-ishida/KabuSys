# Changelog

すべての重要な変更点はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

現在のバージョン: 0.1.0

## [0.1.0] - 2026-04-16
初回公開リリース。コア機能群（実行エンジン、監視、設定管理、ポートフォリオ構築、研究用ファクター計算、ニュース NLP、ユーティリティ、検証ツール）を含みます。

### 追加 (Added)
- 全体
  - パッケージ初期版を導入。バージョン情報は kabusys.__version__ = "0.1.0"。
  - モジュール分割により、実運用エンジン、監視、研究、ポートフォリオ関連処理、ツール等を明確に分離。

- 実行 / ランタイム
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合に専用 SQLite（data/paper_trading.db）へ記録し、本番 DB から分離。
    - BrokerClientFactory によるブローカークライアント生成を採用（実ブローカ／モックの切替）。
    - ExecutionEngine を別スレッド（daemon）で実行し、data/stop_requested.flag による安全停止をサポート。
    - PID ファイル書き出し用のパスを扱う機能を組み込み。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）を検出してループ終了。
    - 監視は環境に依らず本番用 sqlite_path を使用する実装。

- 設定関連
  - config.py: Settings クラスを追加し、環境変数による設定を一元化。
    - .env 自動ロード機能（.env < .env.local、OS 環境変数を保護）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションあり。
    - export KEY=val 形式やクォート／エスケープされた値のパースに対応する .env パーサを実装。
    - 各種設定項目（DB パス、PID パス、しきい値、KABUSYS_ENV 検証、PAPER_FILL_MODE 検証など）をプロパティとして提供。
    - settings（モジュールレベルインスタンス）をエクスポート。

- ポートフォリオ構築
  - portfolio.portfolio_builder: シグナル選定(select_candidates)、等金額／スコア加重重み計算(calc_equal_weights, calc_score_weights) を追加。
  - portfolio.position_sizing: position size（株数）計算ロジックを追加。
    - risk_based / equal / score の allocation_method に対応。
    - lot_size（単元）で丸め、max_position_pct / max_utilization / cost_buffer を考慮したスケーリング／端数処理の実装。
  - portfolio.risk_adjustment: セクター上限適用（apply_sector_cap）とレジーム乗数(calc_regime_multiplier) を追加。
    - unknown セクターはセクター上限の対象外として扱う挙動を採用。
    - レジームに対する乗数マップ（bull/neutral/bear）を実装し、未知レジームは 1.0 でフォールバック。

- 研究（Research）
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を用いた SQL ベース実装）を追加。
    - mom_1m / mom_3m / mom_6m / ma200_dev、atr_20 / atr_pct / avg_turnover / volume_ratio、per / roe 等を算出。
    - データ不足時は None を返す方針を採用。
  - research.feature_exploration: 将来リターン計算 (calc_forward_returns)、IC 計算 (calc_ic)、ファクター統計サマリ (factor_summary)、ランク変換 (rank) を追加。
    - calc_ic はスピアマン相関（ランク）を実装。サンプル数不足時は None を返す。
    - 外部依存（pandas 等）なしで標準ライブラリのみで実装。

- ニュース NLP / AI
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores テーブルへ書き込む処理を追加。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）に基づく記事集約。
    - 1銘柄あたり最大記事数と文字数でトリム（トークン対策）。
    - 最大 20 銘柄ずつバッチ送信、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - レスポンスバリデーションやスコアの ±1.0 クリッピング、部分成功時の既存スコア保護（対象コードのみ削除→挿入）などを採用。
    - OpenAI API キー未設定時は ValueError を送出。

- ユーティリティ
  - utils.process_priority: プロセス優先度設定 set_process_priority(level) を追加。
    - Windows と POSIX (Linux/Mac/FreeBSD) の差を吸収して使える API を提供。
    - CPU affinity 設定用 set_cpu_affinity(cpu_count) を追加。
    - 権限不足や未対応 OS の場合は警告ログを出してスキップ。
  - tools.paper_verification_report: Paper Trading 用検証レポート生成ツールを追加（CLI）。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を集計して PASS/FAIL 判定を行う。閾値はソース内に定義（例: uptime >= 99%、fill_rate >= 90% 等）。
    - DB パスは --db または PAPER_TRADING_SQLITE_PATH で指定可能。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### ドキュメント/設計注記 (Notes)
- .env パーシングはシェル互換の完全準拠ではなく、一般的なケース（export プレフィックス、クォート、インラインコメント）に対応する軽量実装です。
- DuckDB の executemany の制約（空パラメータ非対応）への注意書きや、price 欠損時の将来改善 todo（前日終値フォールバック等）をソース内に記載。
- news_nlp モジュールは API 呼び出しが中心のため、API キー・ネットワークエラーに対してフォールトトレラント（失敗時はスキップして続行）な設計を採用。
- calc_position_sizes 等は実運用のリスクパラメータ（risk_pct、stop_loss_pct、max_position_pct 等）に依存するため、実運用前にパラメータチューニングが必要。

### 既知の制限 (Known issues)
- ai.news_nlp のソースは途中で切れている（現行ツリーでは一部実装が長いため省略箇所がある可能性があります）。実行前に全関数が揃っていることを確認してください。
- price の欠損（0 や None）がある銘柄は一部計算でスキップされるため、想定より候補数が少なくなる場合があります。
- process_priority の優先度設定は権限（root / 管理者）を必要とする場合があり、失敗時は単に警告ログを出力して続行します。

---

今後のリリースでは、以下の点を改善・追加予定です：
- ニュース NLP の完全な実行パス（API レスポンス処理と DB 書き込み周り）の検証とテストカバレッジ拡充。
- position_sizing の銘柄別 lot_size サポート（stocks マスタとの連携）。
- .env パーサの互換性強化（複雑なエスケープ・改行含むケースへの対応）。
- 監視・実行エンジンの監視メトリクス拡張と可観測性向上（メトリクス出力 / Prometheus 等連携）。