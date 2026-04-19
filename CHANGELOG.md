# CHANGELOG

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
語彙は日本語で書かれており、各リリースに含まれる追加・変更点・修正点を要約しています。

## [0.1.0] - 2026-04-19
初回リリース

### 追加 (Added)
- コアランタイム / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時には専用の MockBrokerClient と paper_trading 用 SQLite を使用して本番 DB と完全に分離。  
    - エンジンはデーモンスレッドで起動、停止フラグ検出時に安全に停止。
  - run_monitoring.py: システム監視ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視モジュールは環境にかかわらず本番 sqlite_path を参照する設計（意図的な分離）。

- 設定管理 / CLI
  - config.py: 設定読み込みと Settings クラスを実装。  
    - .env 自動読み込み（.env / .env.local、OS 環境変数保護機構を備える）。  
    - .env パースは export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント等に対応。  
    - 各種設定プロパティ（DB パス、PAPER_FILL_MODE 検証、閾値、PID/kill flag パス 等）を提供。
  - config_setup.py: 対話式 .env ウィザードを追加（.env の初期作成 / 更新を支援）。  
    - 各設定項目の説明・デフォルト・シークレット扱い表示をサポート。  
  - validate_config.py: 起動前設定検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース（PyYAML があれば）を実施。  
    - --strict モードで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio:
    - portfolio_builder.py: 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。  
      - スコア加重で全スコアが 0 の場合は等金額配分にフォールバック（警告ログ）。
    - risk_adjustment.py: セクター集中制限とレジーム乗数（apply_sector_cap, calc_regime_multiplier）。  
      - unknown セクターはセクター上限適用対象外。レジーム不明時は 1.0 でフォールバック（警告ログ）。
    - position_sizing.py: 発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap（スケールダウン）処理、cost_buffer を考慮した保守的見積り。
  - モジュールの純粋関数化によりユニットテストしやすい設計。

- ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。  
    - stdout ストリームハンドラ + 日次ローテートファイルハンドラ（TimedRotatingFileHandler）を設定。  
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度 / CPU affinity 設定ユーティリティを追加。  
    - Windows / POSIX(nice) の差分を吸収。権限不足や未対応 OS の場合は警告を出してスキップ。

- モニタリング関連
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプトで呼び出し、監視用テーブルが存在することを冪等的に保証。

- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。  
    - 稼働率、注文成功率・送信率、リスク却下数、平均/最大/P95 レイテンシを計算して判定（閾値はソース内定義）。  
    - 日付フィルタ、DB パス指定対応。P95 は独自実装。

- パッケージ情報
  - kabusys.__init__ にてバージョンを "0.1.0" として初回設定。

### 変更 (Changed)
- ロギング挙動の統一化:
  - すべての起動スクリプトから setup_logging を呼ぶことでログ出力の一貫性を確保（stdout を使用、ファイルは日次ローテート）。
- DB 接続ポリシー:
  - run_execution は paper_trading モード時に paper_sqlite_path を使用して本番 DB と分離。
  - run_monitoring は設計上、本番 sqlite_path を使用（監視 DB は環境に依存しない構成）。

### 修正 (Fixed)
- .env 読み込みの堅牢化:
  - クォートありの値でのバックスラッシュエスケープ処理、export プレフィックスやインラインコメントの取り扱いを改善。
  - OS 環境変数を保護するための protected パラメータを導入（.env.local の上書き制御など）。

- ログハンドラ二重登録防止:
  - setup_logging 実行時に既存ハンドラを flush/close/削除してから再設定するようにして二重登録を防止。

- プロセス優先度設定の例外ハンドリング:
  - 権限不足や未サポート機能の例外を捕捉して警告ログを出力するよう改善。

### 注意点 / 既知の挙動 (Notes / Known issues)
- run_monitoring は設計上、本番用 sqlite_path を参照します。テスト・開発用途で監視データを分離したい場合は DB パスの運用・環境設計に注意してください。
- position_sizing の価格フォールバックは未実装（price が欠損・0 の場合は当該銘柄をスキップ）。将来的に前日終値等のフォールバックを検討する旨コメントあり。
- config_setup により生成される .env は機密情報を含むため、絶対にリポジトリにコミットしないでください（ヘッダにも注記あり）。
- validate_config は PyYAML 未インストール時に YAML 内容検証をスキップ（警告を出力）。

### 内部 (Internal)
- モジュール分割により関心事が分離（設定・起動スクリプト・ポートフォリオロジック・ユーティリティ・ツール）。  
- 多くの関数は副作用を持たない純粋関数として実装され、テスト容易性を重視。

### セキュリティ (Security)
- このリリース時点で特別なセキュリティ修正はありません。機密情報（API トークン等）は .env 経由で管理する想定のため、運用時は .env の取り扱いに注意してください。

---

今後のリリースで予定している改善（例）
- position_sizing の price フォールバック実装（前日終値や取得原価の参照）。  
- strategy / research のファクター計算やシグナル生成の追加（factor_research 等の拡張）。  
- 起動スクリプトのユニットテスト / E2E テスト自動化。