# KabuSys

KabuSysは、日本株の自動売買システムのための軽量なフレームワーク（骨組み）です。データ取得、ストラテジー開発、注文実行、監視の各コンポーネントを分離して実装できるように設計されています。現状はパッケージの基本構造のみを提供しており、各モジュールは拡張して実用的な自動売買システムを構築することを想定しています。

バージョン: 0.1.0

---

## 機能一覧

- data: 市場データの取得／整形を行うための場所（取得器、キャッシュ、変換処理などを実装）
- strategy: トレードロジック（シグナル作成、ポジション管理など）を実装するための場所
- execution: 注文送信・約定管理・APIラッパを実装するための場所
- monitoring: ログ、アラート、ダッシュボード連携など監視機能を実装するための場所

現状はモジュールのスケルトンのみを提供しているため、ユーザー側で具体的な実装（kabuステーションや他のブローカーAPI、データソースとの接続等）を追加してください。

---

## セットアップ手順

以下は開発・実行のための一般的な手順です。プロジェクトに `pyproject.toml` / `setup.py` / `requirements.txt` がある場合は、それに従ってください。

前提
- Python 3.8 以上を推奨

手順:

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境を作成して有効化（推奨）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存関係をインストール
   - 依存ファイルがある場合:
     ```
     pip install -r requirements.txt
     ```
   - 開発中にローカルパッケージとして使う場合（プロジェクトルートに packaging ファイルがあることが前提）:
     ```
     pip install -e .
     ```

4. （任意）テストやリンターのセットアップ
   - pytest、mypy、flake8 等を導入してコード品質を保つことを推奨します。

---

## 使い方

現状はパッケージスケルトンのみのため、まずは各モジュールに実装を追加してください。基本的な使用例（インポートやバージョン確認）:

```python
from kabusys import __version__
import kabusys.data as data
import kabusys.strategy as strategy
import kabusys.execution as execution
import kabusys.monitoring as monitoring

print("KabuSys version:", __version__)
```

モジュール実装のサンプル（推奨インターフェース例）

- data モジュールに adapter を作る例:
```python
# src/kabusys/data/adapter.py
class MarketDataAdapter:
    def fetch_ohlcv(self, symbol: str, start: str, end: str):
        """OHLCVデータを取得してDataFrameなどで返す"""
        raise NotImplementedError
```

- strategy にシグナル生成クラスを作る例:
```python
# src/kabusys/strategy/base.py
class Strategy:
    def on_market_data(self, ohlcv):
        """新しい市場データを受取って、シグナルを返す"""
        raise NotImplementedError
```

- execution に注文実行インターフェース:
```python
# src/kabusys/execution/client.py
class ExecutionClient:
    def send_order(self, symbol: str, side: str, quantity: int, price: float = None):
        """注文を送信し、注文IDなどを返す"""
        raise NotImplementedError
```

- monitoring にログ／アラート:
```python
# src/kabusys/monitoring/logger.py
def log_event(event: str, level: str = "info"):
    """イベントを記録するためのユーティリティ"""
    pass
```

上記はあくまで例です。プロジェクトの要件に合わせてAPIや戻り値の仕様を決定してください。

ワークフロー例:
1. data.Adapter で市場データを取得
2. strategy.Strategy がデータを受け取り売買シグナルを生成
3. execution.Client がシグナルに基づき注文を発行
4. monitoring で状態・約定・エラーを監視・記録する

---

## ディレクトリ構成

現在の主要ファイル構成:

```
.
├── src/
│   └── kabusys/
│       ├── __init__.py          # パッケージ定義（version, __all__）
│       ├── data/
│       │   └── __init__.py
│       ├── strategy/
│       │   └── __init__.py
│       ├── execution/
│       │   └── __init__.py
│       └── monitoring/
│           └── __init__.py
```

開発を進める際は、各サブパッケージにモジュール（例: adapter.py, client.py, base.py, utils.py など）やテストディレクトリ（tests/）を追加してください。

---

## 開発と拡張のヒント

- 小さな単位（データ取得、戦略、注文実行、監視）ごとに責務を分け、テストを用意する。
- 実際のブローカーAPI（kabuステーション等）と連携する場合は、接続・認証・エラーハンドリング・レート制限に注意する。
- シミュレーション（バックテスト）とリアル注文の実行を分離するアーキテクチャにすると安全。
- ログ、メトリクス、アラートは早期に設計しておくと運用が楽になる。

---

必要があれば、README にサンプル実装（簡易な戦略とモックのExecutionClient）やCI設定、パッケージング手順（pyproject.toml の例）を追記します。どういう使い方／機能を優先して実装したいか教えてください。