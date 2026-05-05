# TODO: ペーパートレード（テスト運用）E2E検証環境の整備

## 1. 背景と目的
運用大詰めにおける本番環境移行前のステップとして、日をまたぐ継続的なテスト運用（ペーパートレード）を実施したい。
しかし、現状のシステムは本番稼働を前提としており、テスト時に「特定のシナリオを能動的に検証する機能」や「日次再起動をまたいでモック口座の状態を維持する機能」が不足している。

また、より本番に近いテストを行うため、**kabuステーション検証環境（ポート18081）を使ったペーパートレード**の仕組みも整備する。kabuステーションAPIは「本番用（ポート18080）」と「検証用（ポート18081）」の2環境を提供しており、検証環境は常に一定の値を返し実際の発注は行われないため、APIの接続性・認証フロー・レスポンス処理を本番と同じコードパスでテスト可能である。

本TODOでは、上記の2つのアプローチ（①Pure Mock による簡易テスト、②kabu検証環境によるリアルなE2Eテスト）を整備し、数日〜数週間にわたる継続的なペーパートレード運用を可能にする。
（※以前の `TODO_DummySignalInjector.md` の要件も本ドキュメントに統合・吸収する）

---

## 2. 実装要件

### [ ] 1. 特定の銘柄のシグナルを注入するCLIツール
- **課題**: 任意の銘柄が意図通りに発注・約定・リスク管理（ストップロス等）されるかをテストしたい場合、夜間バッチで偶然その銘柄のシグナルが出るのを待つか、手動でSQLを叩いて直接書き込む必要がある。
- **対応**: 指定した銘柄・数量・売買区分のテスト用シグナルを `signal_queue` テーブルに注入する専用CLIを作成する。
- **実装詳細**:
  - ファイルパス: `src/kabusys/tools/inject_dummy_signal.py`
  - `argparse` で `--code`, `--side`, `--qty`, `--date` を受け取る。
  - DuckDB の `signal_queue` テーブルに対し、本番バッチと同じスキーマ形式を満たすレコードをINSERTする。

### [ ] 2. ペーパートレード用仮想資金の設定化
- **課題**: `MockBrokerClient` の初期資金が `10,000,000.0` (1000万円) でコード内にハードコードされている。ユーザーが想定する実際の運用予定資金（例: 300万円）でのドローダウンや資金上限のテストが行えない。
- **対応**: 環境変数 `.env` にてテスト用の資金を設定可能にする。
- **実装詳細**:
  - `PAPER_TRADING_INITIAL_CASH` を `.env` および `config.py` に追加（未設定時のデフォルトは1000万とする）。
  - `BrokerClientFactory` にて `mock=True` で生成する際、この設定値を `available_cash` 引数として渡す。

### [ ] 3. モックブローカーの状態復元機能（継続運用への対応）
- **課題**: `TradingRunbook.md` の運用設計に従い Execution Engine を毎日終了・再起動すると、`MockBrokerClient` のメモリ上の口座情報が初期化され、「設定金額・保有ゼロ」に戻ってしまう。これにより、前日に買った株がモック口座から消滅し、DBとの間にリコンシリエーションエラーが発生するため、日をまたぐ運用検証ができない。
- **対応**: Executionエンジン（ペーパートレードモード）起動時に、DBから前日の状態を読み込み、モックブローカーの初期状態として復元する。
- **実装詳細**:
  - `src/kabusys/run_execution.py` でモックブローカーを初期化する際、`OrderRepository` などを通じて `data/paper_trading.db` から直近の「現金の増減（または最新の残高）」と「保有ポジション一覧」を取得する。
  - 取得した状態を `MockBrokerClient` の `initial_positions` 等の引数に注入し、プロセス再起動前と同じ状態を再現する。

### [ ] 4. テスト用DB環境のリセット機能
- **課題**: テスト運用を何度も繰り返すと `data/paper_trading.db` にテスト用の注文やポジションなどのゴミデータが蓄積する。これを手動でDBファイルを削除してリセットするのはオペレーションミスを誘発する。
- **対応**: テスト環境をクリーンな初期状態にワンコマンドで戻す機能を提供する。
- **実装詳細**:
  - `scripts/setup_db.py` に `--paper-reset` オプションを追加する。
  - このオプションが指定された場合、既存の `data/paper_trading.db` が存在すれば削除してから、再度空のテーブルを初期化する挙動とする。

### [ ] 5. kabuステーション検証環境（ポート18081）を使ったペーパートレード対応

> 参考: [kabuステーションAPIドキュメント（Excelアドオン）](https://kabucom.github.io/kabusapi/ptal/add-in.html)

- **背景**: 現在のペーパートレードは `MockBrokerClient`（完全なモック）を使っており、kabu APIには一切接続しない。そのため、「APIの認証フロー」「レスポンスパース」「エラーハンドリング」「WebSocket Push」などの本番コードパスがテストできない。
  kabuステーションは「検証用環境（ポート18081）」を提供しており、実際に発注は行われないが本番と同じAPIを通じて操作できる。これを使うことで、より本番に近いE2Eテストが可能になる。

- **kabuステーションの2つの環境**:
  | 環境 | ポート | 用途 |
  |---|---|---|
  | 本番用 | `18080` | 実際の残高・発注・リアルタイムデータ |
  | 検証用 | `18081` | 常に一定値を返す。実際の発注は行われない |

- **現状の実装**:
  - `KabuStationClient.__init__` のデフォルト `base_url` は `http://localhost:18080/kabusapi`（本番）。
  - `config.py` の `kabu_api_base_url` は `KABU_API_BASE_URL` 環境変数で上書き可能。
  - `broker_factory.py` では `is_paper` の場合 `MockBrokerClient` を返し、`KabuStationClient` は呼ばれない。

- **課題**: `KABUSYS_ENV=paper_trading` のときも `KabuStationClient`（検証環境接続）を使う選択肢がなく、kabu APIの接続テストが本番起動時まで一切できない。

- **対応**: `KABUSYS_ENV` に加え、`KABU_USE_SANDBOX` などのフラグを設けることで、「ペーパートレードモードで、かつkabu検証環境（ポート18081）に接続する」モードを追加する。

- **実装詳細**:
  - `config.py` に `kabu_use_sandbox` プロパティを追加（環境変数: `KABU_USE_SANDBOX`、デフォルト: `false`）。
  - `.env` に `KABU_SANDBOX_API_PASSWORD`（検証環境用APIパスワード）を追加。検証・本番でAPIパスワードが異なるため、別キーとして管理する。
  - `broker_factory.py` を改修し、`is_paper` かつ `kabu_use_sandbox=True` の場合は `KabuStationClient` を検証URL（`http://localhost:18081/kabusapi`）で生成して返す。
  - `validate_config.py` に、`KABU_USE_SANDBOX=true` のときは `KABU_SANDBOX_API_PASSWORD` が設定されているかを検証する項目を追加する。

- **運用フロー（検証環境ペーパートレード）**:
  ```
  1. kabuステーションを起動し、ポート18081（検証用）でログインする。
  2. .env に KABUSYS_ENV=paper_trading / KABU_USE_SANDBOX=true / KABU_SANDBOX_API_PASSWORD=xxxx を設定する。
  3. KABUSYS_ENV=paper_trading python -m kabusys.run_execution で起動する。
  4. KabuStationClient（検証環境）経由で発注・ポジション照会・約定確認のコードパスが実行される。
  ```

- **注意事項**:
  - 検証環境は「常に一定の値を返す」仕様のため、銘柄ごとの価格は固定値になる。実際の市場価格と連動した損益計算の検証はできない。
  - 本番環境への誤接続を防ぐため、`KABU_USE_SANDBOX=true` のときは `KABU_API_PASSWORD`（本番パスワード）を使わず `KABU_SANDBOX_API_PASSWORD` のみを使う設計とする。
