# KabuSys

KabuSys は日本株向けの自動売買システムの骨組み（スケルトン）です。モジュール構成を分離しており、データ取得、売買ロジック（ストラテジー）、注文実行、監視／ログの各機能を独立して実装できるようになっています。

バージョン: 0.1.0

---

## 概要

このリポジトリは、以下の4つの主要コンポーネントに分かれた日本株自動売買システムのベースとなるパッケージ `kabusys` を提供します。

- data: 市場データの取得／管理
- strategy: 売買戦略の実装
- execution: 注文発行・約定処理
- monitoring: ログ、メトリクス、監視・通知

現状はパッケージの基本構成のみが含まれており、各モジュールの具体的な実装（API呼び出し、アルゴリズム、取引所接続など）はこれから追加する想定です。

---

## 機能一覧（予定／想定）

- 市場データの取得・キャッシュ（日次・分足など）
- 複数ストラテジーの実装・管理
- 注文の送信、確認、キャンセル、約定管理
- 取引状況のログ化・通知（メール/Slack等）
- リアルタイム監視ダッシュボード（将来的に統合）

（※ 現リポジトリは構造のみの提供です。上記機能は各モジュールに実装してください）

---

## セットアップ手順

推奨環境
- Python 3.8 以上

1. リポジトリをクローンします。

   ```
   git clone <このリポジトリのURL>
   cd <リポジトリ名>
   ```

2. 仮想環境を作成して有効化します（例: venv）。

   macOS / Linux:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   Windows (PowerShell):
   ```
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. 依存パッケージがある場合は `requirements.txt` を作成してインストールしてください（現段階では依存ファイルは含まれていません）。

   ```
   pip install -r requirements.txt
   ```

4. 開発中にパッケージを import できるように、プロジェクトルートから `src` を PYTHONPATH に含めるか、ローカル editable インストールを行います。

   a) PYTHONPATH を設定する例（セッション単位）:
   ```
   export PYTHONPATH=$(pwd)/src:$PYTHONPATH    # macOS / Linux
   set PYTHONPATH=%cd%\src;%PYTHONPATH         # Windows (cmd)
   ```

   b) setuptools/pyproject を整備している場合は editable install:
   ```
   pip install -e .
   ```

---

## 使い方（基本）

インポート例:

```python
import kabusys

# バージョン確認
print(kabusys.__version__)

# パッケージ内モジュール（ベース）
from kabusys import data, strategy, execution, monitoring
```

各モジュールは現状空のパッケージです。以下は実装テンプレートの例です（各モジュール内にクラスや関数を追加して利用します）。

例: ストラテジー（擬似コード）

```python
# src/kabusys/strategy/my_strategy.py
class MyStrategy:
    def __init__(self, params):
        self.params = params

    def on_market_data(self, market_data):
        # ロジックを実装してシグナルを返す
        return "BUY"  # 例
```

実行（注文発行）の呼び出し（擬似）:

```python
from kabusys.execution import OrderExecutor

executor = OrderExecutor(api_key="XXX", secret="YYY")
order = executor.place_order(symbol="7203.T", side="BUY", qty=100)
```

監視（擬似）:

```python
from kabusys.monitoring import Monitor

monitor = Monitor()
monitor.log_event("order_placed", {"order_id": order.id})
```

上記はあくまで利用例です。実際のメソッド名や引数は実装に合わせて定義してください。

---

## ディレクトリ構成

現状の主要ファイル構成（抜粋）:

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py            # パッケージ定義 (バージョン等)
│     ├─ data/
│     │  └─ __init__.py         # 市場データ取得関連
│     ├─ strategy/
│     │  └─ __init__.py         # 売買戦略関連
│     ├─ execution/
│     │  └─ __init__.py         # 注文実行関連
│     └─ monitoring/
│        └─ __init__.py         # ログ・監視関連
```

ファイルの説明:
- src/kabusys/__init__.py: パッケージのエントリポイント。バージョン情報と公開モジュールを定義しています。
- src/kabusys/data: 市場データ取得と管理のためのモジュールを置く場所。
- src/kabusys/strategy: 売買戦略（シグナル生成・ポジション管理）を実装する場所。
- src/kabusys/execution: ブローカーAPIや注文処理の実装を置く場所。
- src/kabusys/monitoring: ログ出力、監視、アラート送信の実装を置く場所。

---

## 今後の実装ガイド（簡単）

- data:
  - 取引所・API接続クライアントの作成
  - データキャッシュ・永続化（SQLite / CSV 等）
- strategy:
  - ストラテジー基底クラス（on_tick, on_bar 等）
  - パラメータ管理、バックテスト用インターフェース
- execution:
  - 注文発行、約定確認、エラーハンドリング
  - サンドボックス環境への切替機構
- monitoring:
  - ロギングのフォーマット統一、ログ集約
  - メトリクスの収集（Prometheus等）、アラート連携

---

## 注意点

- 実際の取引を行う場合は、APIキー管理、例外処理、リスク管理、レート制限、法令順守（金融商品取引法等）を十分に行ってください。
- 本リポジトリはサンプルの構成のみを提供しており、実取引可能な実装は含まれていません。

---

必要であれば、README に含めるサンプル実装（簡単なデータ取得クラスやストラテジーの雛形）や、pyproject.toml / setup.cfg のテンプレートを作成します。どの部分を優先して追加したいか教えてください。