# KabuSys

KabuSys は日本株の自動売買システム向けの軽量なフレームワーク（スケルトン）です。モジュール化された構成で、データ取得、戦略ロジック、注文実行、監視機能をそれぞれ独立したパッケージとして実装できるよう設計されています。

- バージョン: 0.1.0
- 説明: KabuSys - 日本株自動売買システム（骨組み／テンプレート）

---

## 機能一覧（設計上の責務）

現在のリポジトリはフレームワークの基本構造（パッケージ）を提供します。個別の機能は各モジュールに実装することを想定しています。

- モジュール化された構成
  - data: 市場データ取得、履歴データ管理など
  - strategy: トレーディング戦略の実装ポイント
  - execution: 注文送信・約定処理・証券会社API連携
  - monitoring: ログ、メトリクス、状態監視
- バージョン情報（`kabusys.__version__`）を提供
- 拡張しやすいディレクトリ構成（srcレイアウト）

注意: 本リポジトリは「スケルトン（雛形）」です。実際のデータ取得や注文送信の実装、外部ライブラリやAPIキーの設定などは含まれていません。利用時は各モジュールに必要な実装を追加してください。

---

## セットアップ手順

1. 前提
   - Python 3.8 以上を推奨（プロジェクト要件に応じて変更してください）
   - 仮想環境を利用することを推奨

2. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

3. 仮想環境の作成（例）
   - venv を使用する場合:
     ```
     python -m venv .venv
     source .venv/bin/activate    # macOS / Linux
     .venv\Scripts\activate       # Windows
     ```

4. パッケージのインストール（editable）
   - プロジェクトがpipでインストール可能な構成の場合:
     ```
     pip install -e .
     ```
   - まだパッケージ設定（setup.py/pyproject.toml）が無い場合は、開発時のみ src を PYTHONPATH に含めるか、上記のようにプロジェクトルートから実行してください。

5. 依存関係
   - 本リポジトリには依存ファイルが含まれていません。実際に接続するAPIやデータ処理で使用するライブラリ（requests, pandas, numpy, websocket-client など）を requirements.txt に追加してから `pip install -r requirements.txt` してください。

---

## 使い方（簡易ガイド）

まずはパッケージが import できることを確認します。

Python REPL またはスクリプトで:
```python
import kabusys
print(kabusys.__version__)  # 0.1.0
```

サブパッケージは以下の名前空間で用意されています（現時点では空のパッケージ）:
- kabusys.data
- kabusys.strategy
- kabusys.execution
- kabusys.monitoring

各パッケージに具体的な実装（クラスや関数）を追加して拡張してください。例として、strategy にシンプルな戦略ファイルを追加するテンプレート:

例: src/kabusys/strategy/simple_strategy.py
```python
# simple_strategy.py (テンプレート)
class SimpleStrategy:
    def __init__(self, config):
        self.config = config

    def on_market_data(self, tick):
        """
        市場データが到着したときに呼ばれる想定のメソッド。
        tick: dict や専用オブジェクト（銘柄コード、価格、出来高など）
        戻り値: 'BUY' / 'SELL' / None などのシグナル
        """
        # 実装を追加
        return None
```

実行（execution）モジュールは証券会社APIとのやりとりを担当します。以下は呼び出しの概念例です（実際のAPI呼び出しは証券会社の仕様に従って実装してください）:
```python
from kabusys.execution import Executor  # Executor は仮の例

executor = Executor(api_key="xxxxx")
order_id = executor.send_order(symbol="7203", side="BUY", qty=100, price=1000)
status = executor.get_order_status(order_id)
```

監視（monitoring）モジュールはログや稼働状況の公開、アラート送信などを実装します。Prometheus や Grafana、Sentry 等の統合が考えられます。

---

## ディレクトリ構成

リポジトリに含まれる主要ファイルは以下の通りです。

```
src/
└─ kabusys/
   ├─ __init__.py               # パッケージ初期化。version 定義など
   ├─ data/
   │  └─ __init__.py
   ├─ strategy/
   │  └─ __init__.py
   ├─ execution/
   │  └─ __init__.py
   └─ monitoring/
      └─ __init__.py
```

具体的なファイル（本リポジトリの現状）:
- src/kabusys/__init__.py
- src/kabusys/data/__init__.py
- src/kabusys/strategy/__init__.py
- src/kabusys/execution/__init__.py
- src/kabusys/monitoring/__init__.py

---

## 開発・拡張ガイドライン

- 各サブパッケージに責務を明確に分離する（データ取得 / 戦略 / 実行 / 監視）。
- 外部APIキーや機密情報は環境変数やシークレット管理サービスで管理すること。
- 単体テストを追加する（pytest 等を推奨）。テストディレクトリ例: tests/
- CI を導入し、静的解析（flake8、mypy など）や自動テストを行うと安心です。
- 実運用では必ずペーパートレード・バックテストで挙動を確認すること。

---

## 注意事項

- このプロジェクトは雛形です。実際にマネートレードを行う場合は、十分なテストとリスク管理を行ってください。
- 証券会社APIを直接叩くコードを実装する際は、API利用規約や法令を遵守してください。
- 本リポジトリにはライセンスファイル・利用規約等が含まれていないため、公開・配布時は適切なライセンスを追加してください。

---

必要であれば、READMEに次の内容も追記できます：
- 具体的な依存関係（requirements.txt）
- サンプル戦略の詳細実装
- CI / テスト実行方法
- デプロイ方法（Docker イメージ化、クラウドでの実行例）

追加したいセクションや、実装のテンプレートを希望する場合は教えてください。