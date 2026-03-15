# KabuSys

KabuSysは日本株の自動売買システムのための軽量なPythonパッケージのスケルトンです。現時点ではフレームワーク／骨組みを提供しており、データ取得、売買戦略、注文実行、監視の各コンポーネントを分離して実装できるようになっています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSysは日本株自動売買システムを構築するためのパッケージ構成（モジュール群）を提供します。主な目的は以下です。

- データ取り込み（MARKET、板、約定履歴など）を行う `data` モジュール
- 売買戦略を実装する `strategy` モジュール
- 注文の発注・管理を行う `execution` モジュール
- ログや状態監視・アラートを扱う `monitoring` モジュール

現在はプロジェクトの初期スケルトンのみが含まれており、各サブパッケージに具体的な実装を追加していく想定です。

---

## 機能一覧

- プロジェクト骨組み（パッケージ構造）
  - src/kabusys パッケージ
  - サブパッケージ: data, strategy, execution, monitoring
- バージョン管理（`__version__ = "0.1.0"`）
- 各機能領域を分離した設計により、拡張や単体テストが容易

※ 現在は「テンプレート／骨組み」の段階です。実動作（API接続や戦略実装、注文処理等）は、各サブパッケージに機能を実装してください。

---

## セットアップ手順

前提:
- Python 3.8 以上を推奨

1. リポジトリをクローン（既にコードがある場合はスキップ）
   ```bash
   git clone <リポジトリURL>
   cd <リポジトリディレクトリ>
   ```

2. 仮想環境の作成と有効化（任意だが推奨）
   ```bash
   python -m venv .venv
   # macOS / Linux
   source .venv/bin/activate
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   ```

3. 開発用インストール（パッケージを編集可能な状態でインストール）
   プロジェクトのルートに `setup.py` または `pyproject.toml` がある想定です。無ければ単にパスをPYTHONPATHに追加して使ってください。
   ```bash
   pip install -e .
   ```

   もしパッケージ化していない場合は、直接 `src` をPYTHONPATHに含める方法もあります：
   ```bash
   export PYTHONPATH=$(pwd)/src:$PYTHONPATH   # macOS / Linux
   set PYTHONPATH=%cd%\src;%PYTHONPATH        # Windows (cmd)
   ```

4. 依存ライブラリのインストール
   - まだ requirements ファイルが無ければ、必要に応じて以下のようなパッケージを追加してください（例）:
     ```bash
     pip install requests pandas numpy
     ```

5. APIキーや外部設定
   - 実際に株式売買API（例: kabuステーションや証券会社API）を使う場合は、APIキーやエンドポイントの設定が必要になります。環境変数や設定ファイル（YAML/JSON）などで管理することを推奨します。

---

## 使い方

現状はパッケージのスケルトンのため、基本的なインポートと拡張例を示します。各モジュールに実装を追加して利用してください。

- パッケージをインポートする（例）
```python
import kabusys

print(kabusys.__version__)  # 0.1.0
```

- サブパッケージの利用例（各モジュールに実装を追加した想定）
```python
# 例: データ取得
from kabusys.data import market

df = market.fetch_ticker("7203")  # 銘柄コードを指定して価格データを取得（実装が必要）

# 例: 戦略
from kabusys.strategy import base

class MyStrategy(base.Strategy):
    def on_new_tick(self, tick):
        # 戦略ロジックを実装
        pass

# 例: 実行（注文）
from kabusys.execution import client

client = client.ExecutionClient(api_key="XXX")
order = client.place_order(symbol="7203", side="BUY", qty=100)

# 例: 監視
from kabusys.monitoring import logger

logger.log_info("注文を発注しました")
```

- 開発時の推奨ワークフロー
  1. `data` にAPIクライアント/取得処理を実装
  2. `strategy` に戦略の抽象クラスと具象実装を用意
  3. `execution` に注文発行・キャンセル・注文管理機能を実装
  4. `monitoring` にログ出力、メトリクス収集、アラート機能を実装
  5. 小さな単位で単体テストを作成しCIで自動化

注意: 実際の注文を行う場合はリスクが伴います。まずはペーパートレードやサンドボックス環境で十分に検証してください。

---

## ディレクトリ構成

現状の最小構成は以下の通りです。

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py           # パッケージ初期化（version, __all__）
│     ├─ data/
│     │  └─ __init__.py        # データ取得用サブパッケージ
│     ├─ strategy/
│     │  └─ __init__.py        # 戦略実装用サブパッケージ
│     ├─ execution/
│     │  └─ __init__.py        # 注文実行用サブパッケージ
│     └─ monitoring/
│        └─ __init__.py        # 監視・ログ用サブパッケージ
```

将来的にはそれぞれのサブパッケージに下記のようなファイルを追加することを想定しています（例）:

- src/kabusys/data/
  - market.py
  - historical.py
  - utils.py
- src/kabusys/strategy/
  - base.py
  - mean_reversion.py
  - momentum.py
- src/kabusys/execution/
  - client.py
  - order_manager.py
- src/kabusys/monitoring/
  - logger.py
  - metrics.py
  - alert.py

---

必要に応じて、READMEに動作例やAPI仕様（関数・クラスのインターフェース）を追記していくと使いやすくなります。実装の追加・設計方針についてサポートが必要であればお手伝いします。