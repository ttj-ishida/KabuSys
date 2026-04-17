# Changelog

すべての重要な変更を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン: 0.1.0 — 初期リリース

## [Unreleased]
- ドキュメントやテストの追加、既存機能の微調整などの作業を予定。

---

## [0.1.0] - 2026-04-17

初回公開リリース。以下の機能群とユーティリティを実装しています。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージのメタ情報を `kabusys.__init__` にて `__version__ = "0.1.0"` として定義。

- 環境設定 / ロード
  - `kabusys.config.Settings`：環境変数から各種設定を安全に取得する設定クラスを実装。
  - 自動 `.env` ファイル読み込み機能（プロジェクトルート検出、`.env` / `.env.local` の読み込み順をサポート）。
  - `.env` パーサーは export 形式、クォート、エスケープ、インラインコメント（条件付き）に対応。
  - 環境変数による自動読み込みを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。

- 実行 / 監視用スクリプト
  - `run_execution.py`：ExecutionEngine の起動スクリプトを実装。
    - KABUSYS_ENV が `paper_trading` の場合は paper 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - ブローカークライアント生成（BrokerClientFactory）、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て。
    - RiskManager のデフォルト構成値（max_position_pct 等）を設定。
    - エンジン実行はデーモンスレッドで起動し、プロジェクトルートの停止フラグ（data/stop_requested.flag）検出で停止。
    - 起動時にプロセス優先度を "high" にセット。

  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを実装。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、1 未満の値は無効扱いしてデフォルトにフォールバック）。
    - Monitoring は実行環境に関係なく本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグでループを終了、KeyboardInterrupt を捕捉してクリーンに終了。
    - 起動時にプロセス優先度を "high" にセット。

- DB / Analytics
  - DuckDB / SQLite を利用したデータアクセスを各モジュールで使用（設定によりパスを指定）。
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` 呼び出しで監視用テーブルを冪等に初期化（スクリプトから確実に呼ぶ設計）。

- Portfolio 建構成モジュール
  - `kabusys.portfolio.portfolio_builder`：
    - 候補抽出 (select_candidates)、等配分 (calc_equal_weights)、スコア重み (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等配分にフォールバックし警告ログを出力。
  - `kabusys.portfolio.risk_adjustment`：
    - セクター集中制限適用 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。
    - "unknown" セクターはセクター上限適用対象外。
    - 未知レジームは警告を出して 1.0 でフォールバック。
  - `kabusys.portfolio.position_sizing`：
    - position size 計算ロジック (calc_position_sizes) を実装（risk_based / equal / score の各方式）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate 上限のスケーリング（端数処理で残余キャッシュを使って配分）を実装。
    - cost_buffer による保守的なコスト見積りを考慮。

- 研究・ファクター計算モジュール
  - `kabusys.research.factor_research`：
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、20日平均売買代金、出来高比）、バリュー（PER, ROE）ファクター計算を DuckDB クエリベースで実装。
    - データ不足時の None ハンドリング、ウィンドウスキャン範囲のバッファリング。
  - `kabusys.research.feature_exploration`：
    - 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリ、ランク関数を実装。
    - 外部ライブラリに依存せず、標準ライブラリのみで実装。

- AI ニュース NLP モジュール（ニュースセンチメント）
  - `kabusys.ai.news_nlp`：
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む設計。
    - バッチサイズ、トークン肥大化対策、指数バックオフによるリトライ（429 / ネットワーク / 5xx）などを組み込んだ堅牢設計。
    - API 応答のバリデーション、スコアの ±1.0 クリップ、部分成功時のデータ保護（対象コードで限定して置換）を考慮。
    - ニュース集計ウィンドウ計算ユーティリティ calc_news_window を実装（JST ベースのウィンドウ → UTC 変換）。
    - 注意: 実装は API 呼び出しや記事取得の補助関数が未完（現在一部未完で途中までの実装が含まれます）。

- ツール / レポート
  - `kabusys.tools.paper_verification_report`：
    - Paper Trading 用の検証レポート生成スクリプトを実装（コマンドラインで期間指定可）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
    - デフォルト判定基準を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）。
    - DB 不在やテーブル欠落時に Graceful に N/A を扱う実装。

- ユーティリティ
  - `kabusys.utils.process_priority`：
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（権限不足や未対応 API の場合は警告でスキップ）。
    - 権限不足等での例外をログ警告で扱うフェイルセーフ。

- パッケージエクスポート
  - `kabusys.portfolio` / `kabusys.research` の公開 API を __init__ で整理して利用しやすくエクスポート。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

## 注意事項 / 既知の制約 (Notes / Known limitations)
- news_nlp モジュールは大部分の設計を実装していますが、ファイル末尾で処理が途切れている箇所があります（記事取得や最終処理ロジックの残り実装が必要）。本番運用前に完全実装と十分な API エラー処理の検証を推奨します。
- `.env` パーサーは多くの実用ケースに対処しますが、極端に複雑な入れ子クォートや非標準のシェル構文は想定外の動作をする可能性があります。
- position sizing / allocation の計算では lot_size を全銘柄共通と仮定しています。将来的には銘柄別単元サイズをサポートする予定（TODO コメントあり）。
- プロセス優先度 / CPU affinity の反映は実行環境の権限に依存します。権限不足の場合は警告が出て設定はスキップされます。

---

メンテナンスや次期リリースでは以下を想定しています:
- news_nlp の完実装（記事取得 → OpenAI 呼び出し → DB 書き込みの一連処理の完成）
- 単体テスト・統合テストの整備
- ドキュメント（API 仕様、運用手順、デプロイ手順）の追加
- 個別銘柄ごとの lot_size サポート、より細かなログレベル制御や observability の強化

※ 日付はリポジトリ内のコードから推測した初期リリース日として 2026-04-17 を使用しています。必要に応じて適切なリリース日へ修正してください。