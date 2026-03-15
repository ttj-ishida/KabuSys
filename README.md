# KabuSys

KabuSys は日本株の自動売買システムの骨組み（スケルトン）です。データ取得、売買戦略、注文実行、監視の4つの責務に分割されたモジュール構成を提供し、ユーザーは各モジュールを拡張して自分の自動売買ロジックを実装できます。

バージョン: 0.1.0

---

## 概要

このリポジトリは自動売買システムの基本的なパッケージ構造を提供します。現時点では実装は最小限で、以下のサブパッケージを持つパッケージ（kabusys）として整理されています。

- data: 市場データやヒストリカルデータの取得処理を実装する場所
- strategy: 取引戦略（シグナル生成）を実装する場所
- execution: 注文送信や約定管理を実装する場所
- monitoring: ログ・メトリクス・稼働監視を実装する場所

本プロジェクトは拡張性を重視しており、自分の取引戦略やブローカーAPIに合わせて各モジュールを実装して使います。

---

## 機能一覧

現状は「枠組み（パッケージ、モジュール）」を提供する段階です。将来的に以下のような機能を実装していくことを想定しています。

- モジュール分離された設計（data / strategy / execution / monitoring）
- バージョン情報の管理（kabusys.__version__）
- ユーザーが拡張しやすいインターフェース（strategy, execution 等の実装場所）
- テストやCIを追加しやすい構成

注意: 現時点で具体的なデータ取得ロジックや注文APIとの接続コードは含まれていません。各自の環境に合わせて実装してください。

---

## 動作環境（推奨）

- Python 3.8 以上
- 仮想環境の使用を推奨（venv, pyenv, poetry 等）

必要な外部ライブラリはプロジェクトの用途に応じて追加してください（例: requests, pandas, websocket-client など）。

---

## セットアップ手順

1. リポジトリをクローンします。

   ```
   git clone <repository-url>
   cd <repository-dir>
   ```

2. 仮想環境を作成・有効化します（例: venv）。

   macOS / Linux:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

   Windows (PowerShell):
   ```
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. 開発インストール（編集しながら使う場合）:

   ```
   pip install -e src
   ```

   もしくはパッケージ化してインストールする場合は通常の pip インストールを行います（配布用に setup.py / pyproject.toml を整備してください）。

4. 依存パッケージがある場合は requirements.txt を作成してインストールしてください。

   ```
   pip install -r requirements.txt
   ```

---

## 使い方（基本例）

現状はパッケージと空のサブパッケージを提供しているため、拡張して使用します。下記は典型的な利用フロー（データ取得 → シグナル生成 → 注文実行 → 監視）を示す雛形例です。

1. パッケージのインポートとバージョン確認

   ```python
   from kabusys import __version__, data, strategy, execution, monitoring

   print("KabuSys version:", __version__)
   ```

2. strategy モジュールに戦略クラスを実装する（例）

   src/kabusys/strategy/my_strategy.py
   ```python
   class MyStrategy:
       def __init__(self, params=None):
           self.params = params or {}

       def decide(self, market_data):
           """
           market_data を受け取り、売買シグナルを返す。
           返り値の例: {"action": "buy", "symbol": "7203", "size": 100}
           または None（何もしない）
           """
           # TODO: 戦略ロジックを実装
           return None
   ```

3. execution モジュールに注文送信処理を実装する（例）

   src/kabusys/execution/broker.py
   ```python
   def send_order(order):
       """
       注文をブローカーAPIに送信する処理を実装する。
       order: dict（例: {"action":"buy","symbol":"7203","size":100}）
       """
       # TODO: ブローカーAPI呼び出しを実装
       print("send_order:", order)
       return {"status": "ok", "order_id": "12345"}
   ```

4. 実行フローの例

   ```python
   from kabusys.strategy.my_strategy import MyStrategy
   from kabusys.execution.broker import send_order
   from kabusys.data import some_data_fetcher  # 実装すること

   strat = MyStrategy()
   market_data = {}  # data.some_data_fetcher(...) の結果を入れる
   signal = strat.decide(market_data)
   if signal:
       result = send_order(signal)
       print("order result:", result)
   ```

5. monitoring にログやメトリクス出力を実装する

   src/kabusys/monitoring/logger.py
   ```python
   import logging
   logger = logging.getLogger("kabusys")

   def log_event(msg, level="info"):
       getattr(logger, level)(msg)
   ```

---

## ディレクトリ構成

現時点の主要ファイル・ディレクトリ構成は以下の通りです。

```
.
├── src/
│   └── kabusys/
│       ├── __init__.py        # パッケージ定義 (バージョン、__all__ 等)
│       ├── data/
│       │   └── __init__.py    # データ取得ロジックを実装
│       ├── strategy/
│       │   └── __init__.py    # 戦略実装を配置
│       ├── execution/
│       │   └── __init__.py    # 注文実行・ブローカー連携を実装
│       └── monitoring/
│           └── __init__.py    # ログ・監視処理を実装
└── README.md
```

- src/kabusys/__init__.py には現在以下が定義されています。
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]

---

## 開発と拡張のヒント

- 各サブパッケージ内にインターフェース（ベースクラス）を定義しておくと、異なる実装の差し替えが容易になります。
- ブローカーAPIの認証情報やエンドポイントは環境変数や設定ファイル（yaml/toml/json）で管理することを推奨します。
- リスク管理（ポジションサイズ、サーキットブレーカー等）は execution / strategy の双方で考慮してください。
- ローカルでのテストはユニットテストを用意し、実際の注文送信はモックでテストすることを推奨します。

---

## 貢献・ライセンス

このリポジトリはテンプレート的な構成を提供しています。プルリクエストや Issue は歓迎します。ライセンスはプロジェクトに合わせて追加してください（例: MIT、Apache2.0 など）。

---

ご不明点があれば、どのモジュールにどのような実装を入れたいか教えてください。具体的なコード例（データ取得、戦略アルゴリズム、ブローカー連携）を一緒に作成できます。