# KabuSys

KabuSys は日本株の自動売買システムを想定した Python パッケージの骨組みです。モジュールはデータ取得（data）、売買戦略（strategy）、注文実行（execution）、監視（monitoring）に分かれており、それぞれを実装・拡張して自動売買フローを構築できます。

バージョン: 0.1.0

---

## 概要
このリポジトリは、以下のような自動売買システムの基本構造を提供します。

- データ取得（板情報、約定履歴、日次/分足など）
- 戦略ロジック（シグナル生成、ポジション管理）
- 注文実行（API経由での発注・取消・注文監視）
- 監視・ロギング（取引状態の可視化、アラート）

現状はパッケージの雛形のみが含まれており、各サブパッケージ（data / strategy / execution / monitoring）を実装して拡張していく設計です。

---

## 機能一覧（想定／テンプレート）
- パッケージ分割による責務の明確化
  - data: 市場データの取得・整形インターフェース
  - strategy: シグナル生成・ポジション判定の実装領域
  - execution: ブローカー/API への注文送信や注文管理
  - monitoring: ログ収集、監視・通知フック
- バージョン管理（__version__）
- 将来的にプラグインや複数バックエンドに対応しやすい構成

> 注: 実際の売買APIやデータ取得ロジックは含まれていません。独自に実装してください。

---

## セットアップ手順

前提:
- Python 3.8 以上を推奨

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージのインストール
   - このテンプレートには requirements.txt や pyproject.toml が同梱されていないため、必要なパッケージ（例: requests、pandas、numpy 等）を手動でインストールしてください:
   ```
   pip install --upgrade pip
   pip install pandas numpy requests
   ```

4. 開発モードでインストール（任意）
   - プロジェクトルートに `pyproject.toml` や `setup.cfg` / `setup.py` を用意している場合:
   ```
   pip install -e .
   ```
   - ない場合は、プロジェクトルートを PYTHONPATH に追加するか、スクリプトから相対パスで import してください。

---

## 使い方（基本例・拡張ガイド）

パッケージをインポートしてバージョンを確認する簡単な例:
```python
import kabusys
print(kabusys.__version__)  # 0.1.0
```

サブパッケージ例（実装例を追加して使用）:
```python
# 例: 各サブパッケージでクラスを実装した場合の呼び出しイメージ

from kabusys.data import DataProvider        # 実装: 市場データ取得用インターフェース
from kabusys.strategy import Strategy        # 実装: シグナル生成
from kabusys.execution import Executor       # 実装: 注文送信/管理
from kabusys.monitoring import Monitor       # 実装: ログ/監視

# 各クラスはユーザー側で具体的に実装する想定
data = DataProvider(api_key="XXX")
strategy = Strategy(params={...})
executor = Executor(api_token="YYY")
monitor = Monitor()

# 処理の流れ（概念）
market_data = data.get_latest(symbol="7203")      # 例: トヨタ(7203)
signal = strategy.on_new_data(market_data)
if signal.should_buy:
    executor.send_order(symbol="7203", side="BUY", qty=100)
monitor.record(event="order_sent", details={...})
```

サブパッケージ実装テンプレート（例）:
- data/__init__.py に DataProvider クラスを追加
- strategy/__init__.py に Strategy 抽象クラスを追加
- execution/__init__.py に Executor インターフェースを追加
- monitoring/__init__.py に Monitor/Logger を追加

簡単な Strategy 抽象例:
```python
class BaseStrategy:
    def on_new_data(self, data):
        """
        データ受信時に呼ばれる。シグナルを返す。
        返り値は buy/sell/hold のいずれかまたはカスタムオブジェクト。
        """
        raise NotImplementedError
```

---

## ディレクトリ構成

現在のファイル構成（主要ファイルのみ）:
```
src/
└─ kabusys/
   ├─ __init__.py            # パッケージ定義、__version__
   ├─ data/
   │  └─ __init__.py         # データ取得関連モジュール（実装を追加）
   ├─ strategy/
   │  └─ __init__.py         # 戦略ロジック（実装を追加）
   ├─ execution/
   │  └─ __init__.py         # 注文実行ロジック（実装を追加）
   └─ monitoring/
      └─ __init__.py         # 監視／ロギング（実装を追加）
```

推奨する拡張ファイル例:
- src/kabusys/data/provider.py
- src/kabusys/strategy/base.py
- src/kabusys/strategy/example_strategy.py
- src/kabusys/execution/api_client.py
- src/kabusys/monitoring/logger.py

---

## 開発上の注意点
- 実売買を行う場合は API の仕様（注文レート制限、認証、テスト環境）を十分に確認してください。
- 金融取引はリスクが伴います。バックテストとペーパートレードで十分に検証してください。
- 機密情報（APIキー等）は環境変数や安全なシークレット管理を利用し、コードにハードコーディングしないでください。

---

## 貢献・ライセンス
- このリポジトリはテンプレートです。組織や個人のポリシーに合わせてライセンスを追加してください（例: MIT）。
- バグ修正や機能追加は Pull Request を受け入れるワークフローを推奨します。

---

必要であれば、実際のデータプロバイダ、注文APIラッパー、サンプル戦略、バックテストスクリプトなどの具体的なサンプル実装を追加した README やテンプレートを作成します。どの部分を優先して欲しいか教えてください。