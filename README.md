# KabuSys

KabuSys は日本株の自動売買システム（骨組み）です。データ取得、売買戦略、注文実行、モニタリングの各コンポーネントを分離した構成を想定しており、独自の戦略を実装してすぐに試せるよう設計されています。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 機能一覧
- 要求環境 / 前提
- セットアップ手順
- 使い方
  - 基本的な利用方法
  - 各サブパッケージの役割
  - 簡単な戦略実装例
  - 実行（注文）フロー例
  - モニタリング（ログ／通知）例
- ディレクトリ構成
- 開発ガイド（補足）

---

## プロジェクト概要
KabuSys は日本株の自動売買システムの骨組み（テンプレート）です。以下の主要コンポーネントを備え、実際の取引 API やデータソースに合わせて拡張して使います。

- データ取得（market data / historical）
- 売買戦略（signal generation）
- 注文実行（broker / execution）
- モニタリング（ログ・アラート・監視）

本リポジトリはフレームワークの最小構成を示しており、各モジュールを実装していくことで自動売買システムを構築できます。

---

## 機能一覧
現状（0.1.0）ではパッケージ構成と基本的な API の入り口のみを提供します。具体的な実装はユーザーが追加します。

- パッケージエントリポイント: `kabusys`（バージョン情報含む）
- サブパッケージ（拡張ポイント）
  - `kabusys.data` - 市場データ取り扱い用
  - `kabusys.strategy` - 売買戦略実装用
  - `kabusys.execution` - 注文実行・ブローカー接続用
  - `kabusys.monitoring` - ログや通知（監視）用

将来的には以下を実装することを想定しています（例）:
- 証券会社 API（kabuステーション等）との接続ラッパー
- 過去データの取得・キャッシュ
- バックテスト機能
- リアルタイム注文・リスク管理
- Slack / Email を用いた通知

---

## 要求環境 / 前提
- Python 3.8+ を推奨
- 仮想環境（venv / virtualenv / pyenv）を利用することを推奨
- 実際の注文を行う場合は、利用する証券会社の API キーや認証情報が必要（本リポジトリでは含まれません）

※ 実際の取引を行う場合、十分な理解とテストを行い、リスク管理を徹底してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージのインストール
   - 依存ファイルがある場合は `requirements.txt` や `pyproject.toml` に従ってください。
   - 現状は依存無しの最小構成です。将来的には例えば `requests`, `pandas` などを追加する想定です。

4. 開発中にローカルから使う方法
   - Python のモジュール検索パスに `src` を追加する方法（簡易）
     ```
     export PYTHONPATH=$(pwd)/src:$PYTHONPATH  # macOS / Linux
     set PYTHONPATH=%cd%\src;%PYTHONPATH%      # Windows (cmd)
     ```
   - もしくはプロジェクトにパッケージ設定（pyproject.toml / setup.cfg）を用意して `pip install -e .` を行ってください。

---

## 使い方

### 基本的な使い方（サンプル）
パッケージをインポートして、各モジュールを実装・呼び出す想定です。

```python
from kabusys import data, strategy, execution, monitoring

# 例: データ取得モジュールから価格を取得（実装はユーザー側）
prices = data.get_price("7203")  # 7203: トヨタ（例）
# 例: 戦略でシグナルを作る
sig = strategy.simple_moving_average_signal(prices)
# 例: 実行モジュールで発注
execution.place_order(symbol="7203", side="BUY", size=100)
# 例: モニタリングでログ通知
monitoring.send_alert("Order placed: 7203 BUY 100")
```

上記の関数はサンプルであり、実際のメソッド名や引数は各自で設計してください。

### 各サブパッケージの役割と実装例（案）
- kabusys.data
  - 役割: 株価データ、板情報、約定履歴などの取得・前処理・キャッシュ
  - 実装例:
    - `get_price(symbol: str, start=None, end=None) -> pd.DataFrame`
    - `subscribe_quote(symbol: str, callback: Callable)`

- kabusys.strategy
  - 役割: シグナル生成（売買ロジック）、ポジション管理
  - 実装例:
    - クラスベースで戦略を定義:
      ```python
      class StrategyBase:
          def on_market(self, data):
              raise NotImplementedError
          def on_order_update(self, order):
              pass
      ```
    - 簡単な移動平均クロス戦略などを実装

- kabusys.execution
  - 役割: 注文発注、注文キャンセル、注文状況の取得、約定管理
  - 実装例:
    - `place_order(symbol: str, side: str, size: int, price: float=None)`
    - `cancel_order(order_id: str)`
    - ブローカー API 抽象クラスを用意し、具体実装を差し替える

- kabusys.monitoring
  - 役割: ログ、アラート、ダッシュボード出力
  - 実装例:
    - `send_alert(message: str, level: str="info")`
    - Slack / Email / Webhook にポストするユーティリティ

### 簡単な戦略クラス例（テンプレート）
```python
# src/kabusys/strategy/example.py
from kabusys.data import get_price
from kabusys.execution import place_order

class SimpleStrategy:
    def __init__(self, symbol):
        self.symbol = symbol

    def run(self):
        prices = get_price(self.symbol)
        # シンプルに直近の終値で判断（実際は移動平均などを使う）
        last = prices["close"].iloc[-1]
        # ダミー条件: 直近が閾値より低ければ買い
        if last < 1000:
            place_order(symbol=self.symbol, side="BUY", size=100)
```

### 実行フロー（概念）
1. データモジュールがマーケットデータを取得（履歴 / ストリーム）
2. 戦略モジュールがデータを受け取り売買シグナルを生成
3. 実行モジュールがシグナルに基づき注文を発注
4. モニタリングモジュールがロギング・アラートを行う

---

## ディレクトリ構成
現在の最小構成は以下の通りです。

```
<project-root>/
├─ src/
│  └─ kabusys/
│     ├─ __init__.py           # パッケージメタ情報（__version__, __all__）
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
├─ README.md                   # （このファイル）
# （将来的には下記ファイルを追加）
# ├─ requirements.txt
# ├─ pyproject.toml / setup.cfg
# ├─ tests/
# └─ examples/
```

---

## 開発ガイド（補足）
- テスト: pytest 等を導入してユニットテストを書くことを推奨します。
- 型チェック: mypy や pyright を導入して型定義を整えると保守性が高まります。
- ロギング: 標準の logging を使い、必要に応じて監視モジュールから外部通知を行う設計が良いです。
- 実装上の注意:
  - 実際の注文を行う際は必ずサンドボックスやデモ口座で十分なテストを行ってください。
  - API キー等は環境変数やシークレットマネージャで安全に管理してください（リポジトリに書き込まない）。

---

README に記載した内容は本リポジトリの初期設計・利用例です。実際の自動売買システムを稼働させるには、各コンポーネント（データ取得、戦略、注文実行、監視）を適切に実装・検証してください。必要があれば、テンプレートやサンプル実装を追加していきましょう。