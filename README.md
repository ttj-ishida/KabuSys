# KabuSys

KabuSys は日本株向けの自動売買システムの基盤ライブラリです。データ取得（Data）、売買戦略（Strategy）、注文実行（Execution）、稼働監視（Monitoring）の責務を分離した構成を採用しており、ユーザー独自の戦略や実行モジュールを容易に組み込めるように設計されています。

現在のバージョン: 0.1.0

---

## 主な特徴（機能一覧）

- モジュール化されたアーキテクチャ
  - data: 市場データや履歴データの取得・ラップ
  - strategy: 売買戦略ロジックの実装場所
  - execution: 注文送信や約定管理など実行関連
  - monitoring: 稼働状況のログ/メトリクス収集、アラート
- 拡張しやすいインターフェース設計（各責務ごとに独立）
- テスト・開発しやすい src 配置（src/ パッケージレイアウト）
- 将来的なリアル注文連携（API クライアントの差し替えで実装可能）

> 備考: 本リポジトリは骨組み（スケルトン）であり、実際の取引APIや具体的な戦略ロジックは含みません。独自実装を追加して利用してください。

---

## セットアップ手順

前提:
- Python 3.8 以上を推奨
- 実際の運用では API キーや証券会社との接続情報が必要になります（別途設定してください）

1. リポジトリをクローン（既にクローン済みの場合はスキップ）
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境を作成・有効化
   - macOS / Linux:
     ```
     python -m venv venv
     source venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール
   - このテンプレートは依存ファイルを含みません。プロジェクトで必要なパッケージを追加してください。例:
     ```
     pip install pandas requests websockets
     ```
   - 開発中は編集しやすくするため editable install を推奨:
     - プロジェクトルートに `pyproject.toml` または `setup.py` を用意している場合:
       ```
       pip install -e .
       ```

4. （任意）環境変数や設定ファイルの準備
   - API キーや接続先は `config/` や環境変数で管理してください（実運用では秘密情報の管理に注意）。

---

## 使い方（基本例 / 拡張方法）

このパッケージは各責務ごとにモジュールを分けているため、以下のように各モジュールを実装・拡張して利用します。

- 最小確認: パッケージが読み込めるか確認
```python
import kabusys
print(kabusys.__version__)   # 0.1.0
```

- ディレクトリに用意されたモジュールを拡張する例（擬似コード）

  - data: データプロバイダーを実装
    ```python
    # src/kabusys/data/my_provider.py
    class DataProvider:
        def get_latest_price(self, symbol):
            # API や CSV、DB から価格を取得する処理を実装
            return 1000.0
    ```

  - strategy: 戦略クラスを実装
    ```python
    # src/kabusys/strategy/simple_ma.py
    class SimpleMA:
        def __init__(self, short_window=5, long_window=25):
            self.short_window = short_window
            self.long_window = long_window

        def decide(self, price_series):
            # 単純な移動平均クロスの判断を行い、'buy'/'sell'/None を返す
            return 'buy'
    ```

  - execution: 注文処理の実装（模擬実行や本番APIを差し替え）
    ```python
    # src/kabusys/execution/mock_execution.py
    class MockExecutionClient:
        def send_order(self, symbol, side, quantity):
            # 実際には kabuステーション / 取引API に接続して注文を出す
            print(f"Order: {side} {quantity} {symbol}")
            return {"status": "ok", "order_id": "mock-123"}
    ```

  - monitoring: 稼働状況や例外を監視
    ```python
    # src/kabusys/monitoring/logging_monitor.py
    import logging
    logger = logging.getLogger("kabusys")
    class LoggingMonitor:
        def info(self, msg):
            logger.info(msg)
    ```

- 組み合わせ例
```python
from kabusys.data.my_provider import DataProvider
from kabusys.strategy.simple_ma import SimpleMA
from kabusys.execution.mock_execution import MockExecutionClient
from kabusys.monitoring.logging_monitor import LoggingMonitor

data = DataProvider()
strategy = SimpleMA()
exec_client = MockExecutionClient()
monitor = LoggingMonitor()

price_series = [...]  # 過去価格履歴を取得
signal = strategy.decide(price_series)
if signal == 'buy':
    exec_client.send_order("7203.T", "BUY", 100)
    monitor.info("Bought 7203.T 100 shares")
```

注意:
- 実取引を行う場合は、API レートリミット、約定/注文管理、リスク管理（損切り、最大発注量、ポジション管理）を必ず実装してください。
- 本テンプレートはバックテスト機能を含みません。バックテスト用のモジュールを別途実装することを推奨します。

---

## ディレクトリ構成

現在のリポジトリ（サンプル）の主要ファイル構成は以下の通りです。

- src/
  - kabusys/
    - __init__.py              # パッケージのエントリポイント（バージョン定義など）
    - data/
      - __init__.py
      # データ取得関連モジュールを追加
    - strategy/
      - __init__.py
      # 戦略実装を追加
    - execution/
      - __init__.py
      # 注文実行クライアントを追加
    - monitoring/
      - __init__.py
      # 監視・ログ関連を追加

例（ツリー表示）
```
project-root/
├─ src/
│  └─ kabusys/
│     ├─ __init__.py
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
└─ README.md
```

---

## 開発のヒント / 推奨事項

- バージョン管理: semantic versioning を採用（例: 0.1.0）
- テスト: 各モジュールに対してユニットテストを用意し、CI（GitHub Actions など）で自動実行することを推奨
- 設定管理: API キーや重要設定は環境変数または秘密管理サービスで管理する
- ロギング: 実運用では構造化ログ（JSON）やメトリクス収集（Prometheus 等）を組み合わせると監視が容易
- セーフティ: 実際の注文を出す前に必ずテスト環境／模擬注文で十分な検証をすること

---

必要であれば、この README に具体的なサンプル戦略、サンプル設定ファイル（例: config.yaml）、推奨依存パッケージ一覧、あるいは CI 設定例を追加で作成します。どの追加が必要か教えてください。