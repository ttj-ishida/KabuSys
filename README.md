# KabuSys

日本株自動売買システム（KabuSys）の骨組みパッケージです。  
本リポジトリは、データ取得・ストラテジー実装・注文実行・モニタリングの4つの責務に分割された構成を提供します。各コンポーネントを実装・拡張して、自動売買ロジックを構築するための出発点となります。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークの雛形です。以下の主要コンポーネントを想定しています。

- data: 市場データ（株価、板情報、約定履歴など）の取得と前処理
- strategy: 売買戦略（シグナル生成、ポジション管理）
- execution: 注文発行・約定管理（ブローカーAPI連携／モック）
- monitoring: ログ・メトリクス・稼働状況の可視化、アラート

このリポジトリ自体は最小構成であり、各モジュールの具体的な実装（APIクライアントや具体的な戦略）は含まれていません。利用者は自分の取引ルールや接続先APIに合わせて拡張して使います。

---

## 機能一覧（想定）

現在のリポジトリはパッケージ構造のみを提供します。実装例として期待される機能は次の通りです。

- データ取得
  - 株価（始値・高値・安値・終値・出来高）の取得
  - リアルタイムティッカー / 板情報の取得
  - CSV / DB からのヒストリカルデータ読み込み
- ストラテジー
  - ローソク足、テクニカル指標（移動平均、RSI など）
  - シグナル生成とポジション管理
  - バックテストのインターフェース
- 注文実行
  - ブローカーAPI（例: Kabutan / kabuステーション / その他）との接続
  - 注文登録・取消・注文状態の監視
  - 注文のフェイルセーフ／再試行処理
- モニタリング
  - ログ出力（ファイル／標準出力）
  - メトリクス収集（Prometheus 等）
  - 異常時の通知（メール／Slack 等）

---

## 要件

- Python 3.8+
- 仮想環境の利用を推奨
- 実際にブローカーに接続する場合は当該ブローカーのAPIキーなどの資格情報が必要

（依存パッケージは本テンプレートには明記されていません。実装時に requirements.txt を追加してください）

---

## セットアップ手順

ローカルで開発・実行するための基本手順です。

1. リポジトリをクローンする
   ```
   git clone <リポジトリURL>
   cd <リポジトリディレクトリ>
   ```

2. 仮想環境を作成して有効化する（例: venv）
   - macOS / Linux:
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 開発用依存関係をインストールする
   - 依存ファイルがない場合は個別に追加してください。例:
     ```
     pip install -r requirements.txt
     ```
   - 開発中は editable install を使うと便利です:
     ```
     pip install -e .
     ```

4. 環境変数や設定ファイルを準備する
   - ブローカーAPIキー、エンドポイント、ログ設定などを環境変数や YAML/JSON の設定ファイルで管理してください。
   - 例（環境変数）:
     ```
     export KABU_API_KEY="your_api_key"
     export KABU_API_SECRET="your_api_secret"
     ```

---

## 使い方（基本例）

このパッケージはモジュール群を提供します。ここではテンプレート的な利用例を示します。実際の関数名・引数はプロジェクトで実装してください。

1. パッケージをインポートする
   ```python
   import kabusys
   from kabusys import data, strategy, execution, monitoring
   ```

2. データ取得（実装例）
   ```python
   # data モジュールに get_historical_prices を実装した場合
   prices = data.get_historical_prices(symbol="7203", start="2024-01-01", end="2024-03-31")
   ```

3. ストラテジーでシグナル生成（実装例）
   ```python
   # strategy モジュールでシグナル生成関数を実装
   signals = strategy.generate_signals(prices)
   ```

4. 注文実行（実装例）
   ```python
   # execution モジュールに place_order を実装
   for sig in signals:
       if sig.action == "BUY":
           execution.place_order(symbol=sig.symbol, side="BUY", qty=sig.qty, price=sig.price)
       elif sig.action == "SELL":
           execution.place_order(symbol=sig.symbol, side="SELL", qty=sig.qty, price=sig.price)
   ```

5. モニタリング（実装例）
   ```python
   # monitoring モジュールでログやメトリクスを送る
   monitoring.log_trade(trade_info)
   monitoring.report_metrics(metrics)
   ```

注: 上記はあくまでインターフェースの例です。各モジュールの詳細実装（関数名／返り値／例外処理）はプロジェクトで定義してください。

---

## ディレクトリ構成

現在の主要ファイル/ディレクトリ構成は以下の通りです。

- src/
  - kabusys/
    - __init__.py         (パッケージ初期化、バージョン情報等)
    - data/
      - __init__.py       (データ取得・前処理モジュール)
    - strategy/
      - __init__.py       (ストラテジーモジュール)
    - execution/
      - __init__.py       (注文実行モジュール)
    - monitoring/
      - __init__.py       (モニタリングモジュール)
- README.md              (本ファイル)
- setup.cfg / pyproject.toml / setup.py (プロジェクト設定ファイルは必要に応じて追加)

※ 実装を進める場合は、各モジュール内にサブモジュールや util、tests ディレクトリ等を追加してください。

例（拡張案）:
- src/kabusys/data/clients.py (API クライアント)
- src/kabusys/strategy/backtest.py
- src/kabusys/execution/broker.py
- tests/ (ユニットテスト)

---

## 開発メモ / ベストプラクティス

- ブローカーAPIに接続する部分はテストしやすいようにインターフェースを抽象化し、モックを用意することを推奨します。
- 実取引を行う前にバックテスト・ペーパートレードで十分に検証してください。
- リスク管理（最大ドローダウン、1トレードあたりの最大ポジション、取引時間の制限など）をコードに組み込んでください。
- 機密情報（APIキー等）は環境変数やシークレットストアで管理し、リポジトリに含めないでください。

---

## 貢献・拡張

- イシューやプルリクエスト歓迎です。新しいデータプロバイダ、戦略、エグゼキューションバックエンドを追加する際は、既存のモジュール構成に沿って行ってください。
- README に記載のテンプレート関数名やインターフェースを実際の実装に合わせて更新してください。

---

## 注意事項（免責事項）

本リポジトリは教育・開発目的のテンプレートです。実際の金融取引に用いる場合、法令、ブローカーの利用規約、税務上の取り扱い等を十分に理解した上で自己責任で行ってください。取引による損失について作者・配布者は一切の責任を負いません。

---

もし具体的に実装したい機能（例: 「kabuステーションAPI で板情報を取得するクライアント」や「単純移動平均クロスの戦略実装」）があれば、用途に合わせたテンプレート実装例やサンプルコードを提示します。どの部分から実装を始めたいか教えてください。