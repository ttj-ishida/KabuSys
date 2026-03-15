# KabuSys

KabuSys は日本株の自動売買システムの骨組み（ライブラリ）です。  
現在はパッケージの基本構成（data, strategy, execution, monitoring）のみが用意されており、実際の取引ロジックやAPI連携は各モジュールを実装して拡張する想定です。

バージョン: 0.1.0

---

## 概要

このリポジトリは、自動売買システムを構築するための基本モジュールをまとめた Python パッケージです。  
各モジュールは以下の責務を想定しています。

- data: 市場データの取得・整形
- strategy: 売買戦略（シグナル生成）
- execution: 注文発行（証券会社 API とのやり取り）
- monitoring: ログ・メトリクス・運用監視

現状はモジュールのスケルトンのみ（空のパッケージ）ですが、プロジェクトのベースとして利用できます。

---

## 機能一覧（想定・拡張ポイント）

- 市場データ取得インターフェース（data）
- 戦略（Strategy）を定義するための抽象構造（strategy）
- 注文を出すための実行クライアント（execution）
- 監視・ログ出力・アラート用インターフェース（monitoring）
- Python パッケージとしての配布・バージョン管理

注意: 現在のリポジトリには実装は含まれていません。各モジュールは実装して拡張する必要があります。

---

## セットアップ手順

1. 必要な Python バージョンを用意
   - 推奨: Python 3.8 以上

2. リポジトリをクローン
   ```
   git clone <このリポジトリのURL>
   cd <リポジトリディレクトリ>
   ```

3. 仮想環境を作成して有効化（任意だが推奨）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

4. 開発インストール
   - パッケージを編集可能モードでインストール:
     ```
     pip install -e .
     ```
   - （requirements.txt / setup.cfg が未提供の場合は、依存パッケージを個別にインストールしてください）

5. 環境変数や設定
   - 実際に証券会社 API（例: kabu.com 等）を使う場合は、API キーやシークレットを環境変数または設定ファイルで管理してください。
   - 例:
     - KABUSYS_API_KEY
     - KABUSYS_API_SECRET
     - KABUSYS_ENV (prod / sandbox)

---

## 使い方（拡張方法とサンプル）

本パッケージは名前空間として以下を提供します。

```python
import kabusys

print(kabusys.__version__)  # 0.1.0
# 利用可能なサブパッケージ
# kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring
```

各モジュールを実装する例（概念サンプル）:

- data モジュールの実装例
```python
# src/kabusys/data/provider.py
class DataProvider:
    def fetch_latest(self, symbol):
        """最新のティック/板/終値などを返す（実装必須）"""
        raise NotImplementedError
```

- strategy モジュールの実装例
```python
# src/kabusys/strategy/simple.py
class SimpleStrategy:
    def generate_signal(self, market_data):
        """シグナルを返す: 'buy' / 'sell' / 'hold'"""
        # 実装例: 単純移動平均のクロスなど
        return "hold"
```

- execution モジュールの実装例
```python
# src/kabusys/execution/client.py
class ExecutionClient:
    def place_order(self, symbol, side, quantity):
        """注文送信（証券会社 API を呼ぶ実装）"""
        raise NotImplementedError
```

- monitoring モジュールの実装例
```python
# src/kabusys/monitoring/logger.py
class Monitor:
    def info(self, msg):
        print(msg)
    def alert(self, msg):
        # メール/Slack などに通知する処理
        pass
```

統合例（疑似コード）:
```python
from kabusys.data.provider import DataProvider
from kabusys.strategy.simple import SimpleStrategy
from kabusys.execution.client import ExecutionClient
from kabusys.monitoring.logger import Monitor

data = DataProvider()
strategy = SimpleStrategy()
exec_client = ExecutionClient()
monitor = Monitor()

market = data.fetch_latest("7203.T")  # トヨタの例
signal = strategy.generate_signal(market)

if signal == "buy":
    exec_client.place_order("7203.T", "buy", 100)
    monitor.info("Bought 100 shares of 7203.T")
```

---

## ディレクトリ構成

現在の主要ファイル構成は以下の通りです。

- src/
  - kabusys/
    - __init__.py           （パッケージルート、バージョン指定）
    - data/
      - __init__.py         （データ関連のモジュールを配置）
    - strategy/
      - __init__.py         （戦略関連のモジュールを配置）
    - execution/
      - __init__.py         （注文実行・API クライアントを配置）
    - monitoring/
      - __init__.py         （監視・ログ関連を配置）
- README.md                 （このファイル）
- setup.py / pyproject.toml  （存在する場合はパッケージ設定）

（現在は各サブパッケージの __init__.py が存在するのみで、個別実装ファイルは含まれていません。）

---

## 開発・貢献ガイド（簡易）

- 新しい機能は各サブパッケージ配下にモジュールを追加してください（例: kabusys/data/xxx.py）。
- ユニットテスト、タイプチェック（mypy）や linters（flake8/black）を導入すると運用しやすくなります。
- 実際の売買に使用する前に、必ずペーパートレード・サンドボックス環境で動作検証してください。
- API キーやシークレットは絶対にリポジトリに含めないでください。環境変数または安全なシークレットマネージャを使用してください。

---

## 注意事項

- 本リポジトリは教育・開発用の骨組みです。実際の売買を行うには、証券会社の API の仕様に合わせた実装・安全対策（エラーハンドリング、レート制限、認証、リスク管理等）が必須です。
- 金融取引にはリスクが伴います。本ソフトウェアの利用により発生した損失について作者は責任を負いません。

---

必要があれば、README にサンプル実装、設定ファイルのテンプレート、テストの雛形などを追加して作成します。どの部分を優先して詳細化しますか？ (例: data/provider の実装例、kabu.com API 統合、CI/CD の設定 など)