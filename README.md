# KabuSys

KabuSys は日本株向けの自動売買システムの骨組み（テンプレート）です。モジュール化された設計により、データ取得、売買戦略、注文実行、モニタリングの各コンポーネントを分離して開発できます。

現在のバージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 機能一覧
- 要求環境
- セットアップ手順
- 使い方
- 開発ガイド（簡易）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は教育用／開発用の自動売買フレームワークの雛形です。各サブパッケージを実装することで、実際のデータ取得や売買ロジック、ブローカー API への発注、運用時の監視機能を追加できます。

メインパッケージ:
- kabusys.data: 市場データ取得・整形
- kabusys.strategy: 売買戦略（シグナル生成、ポジション管理）
- kabusys.execution: 注文発注・約定管理
- kabusys.monitoring: ログ、メトリクス、アラート

---

## 機能一覧
現状（テンプレート段階）で提供するもの:
- プロジェクトのパッケージ骨組み（モジュール分割）
- バージョン情報（__version__ = "0.1.0"）
- 各サブパッケージのプレースホルダ

想定して拡張する機能（今後の実装例）:
- リアルタイム／過去データ取得モジュール（API クライアント）
- テクニカル指標、シグナル生成
- 注文管理（成行／指値／取消）
- 監視ダッシュボード、アラート（メール／Slack 等）
- バックテスト機能

---

## 要求環境
- Python 3.8 以上（プロジェクトポリシーに応じて調整）
- 依存パッケージは現状なし。外部 API や追加機能を実装する場合はそれに応じたライブラリを追加してください（例: requests, pandas, numpy, websockets など）。

---

## セットアップ手順（開発環境）
1. リポジトリをクローン:
   ```
   git clone <リポジトリURL>
   cd <リポジトリ名>
   ```

2. 仮想環境を作成・有効化（例: venv）:
   ```
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. 必要なら依存をインストール（requirements.txt があれば）:
   ```
   pip install -r requirements.txt
   ```
   現状は依存がないためこのステップは不要です。

4. 開発モードでインストール（プロジェクトに pyproject.toml / setup.py / setup.cfg を用意している場合）:
   ```
   pip install -e .
   ```
   もしパッケージ化ファイルがない場合は、開発中はプロジェクトルートの `src` を PYTHONPATH に追加するか、エディタの設定で参照してください。

---

## 使い方（簡単な例）
パッケージがインポート可能な状態であれば、下記のように利用します。

Python インタプリタまたはスクリプト内で:
```python
import kabusys

# バージョン確認
print(kabusys.__version__)  # => "0.1.0"

# サブパッケージ参照（現状はプレースホルダ）
import kabusys.data
import kabusys.strategy
import kabusys.execution
import kabusys.monitoring

print(kabusys.__all__)  # => ["data", "strategy", "execution", "monitoring"]
```

各サブパッケージに機能を実装したら、実際のデータ取得→シグナル生成→発注→監視のフローを組み立ててください。

簡単なフロー（擬似コード）:
```python
from kabusys.data import DataFetcher
from kabusys.strategy import Strategy
from kabusys.execution import Executor
from kabusys.monitoring import Monitor

data = DataFetcher(...)
strategy = Strategy(...)
executor = Executor(...)
monitor = Monitor(...)

prices = data.get_history("7203.T")
signal = strategy.generate_signal(prices)

if signal == "BUY":
    executor.place_order(symbol="7203.T", side="BUY", qty=100)
    monitor.notify("Bought 7203.T")
```
（上記クラスはテンプレートのため、実装が必要です）

---

## 開発ガイド（どこに実装するか）
- ロジックはそれぞれのサブパッケージ内に実装してください。
  - src/kabusys/data: API クライアント、データクレンジング、キャッシュ
  - src/kabusys/strategy: 戦略クラス、バックテスト用インターフェース
  - src/kabusys/execution: ブローカー／証券会社 API ラッパー、注文管理
  - src/kabusys/monitoring: ロギング、アラート、メトリクス収集

- 各モジュールはテスト可能な小さな部品（関数／クラス）に分割すると良いです。

---

## ディレクトリ構成
現状の最小構成:
```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py           # パッケージ定義（バージョン、__all__）
│     ├─ data/
│     │  └─ __init__.py        # データ関連モジュールを置く
│     ├─ strategy/
│     │  └─ __init__.py        # 戦略関連モジュールを置く
│     ├─ execution/
│     │  └─ __init__.py        # 注文実行関連モジュールを置く
│     └─ monitoring/
│        └─ __init__.py        # 監視関連モジュールを置く
```

将来的には各ディレクトリ配下に以下のようなファイルを追加することが考えられます:
- src/kabusys/data/client.py
- src/kabusys/strategy/base.py
- src/kabusys/execution/broker.py
- src/kabusys/monitoring/logger.py
- tests/（テストケース）

---

必要であれば、README に含めるサンプル実装や pyproject.toml / setup.cfg のテンプレートも作成します。どのように拡張したいか教えてください。