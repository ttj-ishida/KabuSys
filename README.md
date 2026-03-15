# KabuSys

KabuSys は日本株の自動売買を目的とした軽量な骨組み（フレームワーク）です。データ取得、売買ロジック（ストラテジー）、注文実行、モニタリングの4つの主要コンポーネントを分離して実装できるように設計されています。

バージョン: 0.1.0

---

## 概要

このリポジトリは、以下のモジュールを持つ Python パッケージ `kabusys` を提供します。

- data: 市場データの取得・加工を担うモジュール
- strategy: 売買ロジック（シグナル生成）を記述するモジュール
- execution: 注文送信や約定処理を行うモジュール
- monitoring: 稼働状況や取引結果の監視・ログ出力・アラートを行うモジュール

現在はパッケージの骨組みのみが含まれており、実際の実装（API 呼び出しや具体的な戦略）は各モジュールに実装する必要があります。

---

## 機能一覧

現状（0.1.0）は以下を含むスケルトン実装です。

- パッケージの基本構成（`kabusys`）
- 主要サブパッケージの定義: `data`, `strategy`, `execution`, `monitoring`
- バージョン情報（`__version__ = "0.1.0"`）

将来的に想定される機能（実装次第で利用可能）:

- リアルタイムおよび過去データの取得（API / CSV / DB）
- 戦略（バックテスト、シグナル生成、ポジション管理）
- 注文発注（各証券会社 API との連携）
- 取引ログ、パフォーマンス集計、アラート（メール/Slack 等）
- バックテスト/フォワードテストのためのシミュレーション環境

---

## セットアップ手順

以下は一般的な開発用セットアップ手順です。実際の依存パッケージは実装に応じて追加してください。

1. Python のバージョンを用意（推奨: 3.8+）

2. リポジトリをクローン
```
git clone <リポジトリURL>
cd <リポジトリ>
```

3. 仮想環境の作成と有効化 (任意だが推奨)
```
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

4. 開発用インストール（プロジェクトルートに pyproject.toml または setup.py がある想定）
```
pip install -e .
```
もしパッケージ管理ファイルが無ければ、単にソースディレクトリを PYTHONPATH に追加して利用できます。

5. 依存パッケージを追加する場合は requirements.txt に記載しておき、インストールします。
```
pip install -r requirements.txt
```

6. （任意）環境変数や API キーの設定
- 各証券会社 API を使う場合は API キーやアカウント情報を環境変数や設定ファイルで管理してください。

---

## 使い方

現状はパッケージの読み込みとモジュール拡張のための雛形を提供しています。基本的な利用例は以下の通りです。

- バージョン確認:
```python
>>> import kabusys
>>> print(kabusys.__version__)
0.1.0
```

- モジュールを拡張して使う（例: Strategy を実装して利用）
```python
# 例: src/kabusys/strategy/sample_strategy.py
from kabusys.strategy import BaseStrategy  # 実装する想定のベースクラス

class MyStrategy(BaseStrategy):
    def on_bar(self, bar):
        # bar を受け取って売買判断を行う
        pass
```

- 実行フローの概念例（擬似コード）
```python
from kabusys.data import DataProvider      # 実装想定
from kabusys.strategy import StrategyBase  # 実装想定
from kabusys.execution import Executor     # 実装想定
from kabusys.monitoring import Monitor     # 実装想定

data_provider = DataProvider(...)
strategy = StrategyBase(...)
executor = Executor(...)
monitor = Monitor(...)

for bar in data_provider.stream("銘柄コード"):
    signal = strategy.on_bar(bar)
    if signal:
        executor.execute(signal)
    monitor.record(bar, signal)
```

- 実装ガイド（推奨インターフェース）
  - data: DataProvider クラスを実装。stream()/get_history() などを提供。
  - strategy: StrategyBase（on_bar, on_tick, initialize など）を実装してシグナルを返す。
  - execution: Executor クラスを実装し、send_order(), cancel_order(), get_positions() 等を実装。
  - monitoring: Monitor によりログ収集・アラート送信を行う。

各サブパッケージに具体的な実装を追加していくことで、自動売買アプリケーションを構築できます。

---

## ディレクトリ構成

リポジトリの主要ファイルとディレクトリ構成（現状）:

```
.
├── src/
│   └── kabusys/
│       ├── __init__.py            # パッケージ定義（version, __all__）
│       ├── data/
│       │   └── __init__.py        # data モジュール（データ取得）
│       ├── strategy/
│       │   └── __init__.py        # strategy モジュール（売買ロジック）
│       ├── execution/
│       │   └── __init__.py        # execution モジュール（注文実行）
│       └── monitoring/
│           └── __init__.py        # monitoring モジュール（監視・ログ）
└── README.md                      # （このファイル）
```

将来的には下記のように拡張することを想定しています:

```
src/kabusys/
├── data/
│   ├── provider.py
│   ├── loaders.py
│   └── utils.py
├── strategy/
│   ├── base.py
│   ├── examples/
│   │   └── moving_average.py
│   └── backtest.py
├── execution/
│   ├── broker_api.py
│   └── simulator.py
└── monitoring/
    ├── logger.py
    ├── alert.py
    └── dashboard.py
```

---

## 開発メモ / 拡張案

- まずは各サブパッケージにベースクラス（抽象クラス）を実装してください。例えば `strategy/base.py` に `StrategyBase` を定義し、サブクラスが `on_bar` 等を実装する形が分かりやすいです。
- 注文実行はリスクが伴うため、まずは `execution/simulator.py` のようなシミュレータを実装してテスト→実証後に本番 API を組み込むことを推奨します。
- 設定や認証情報はコードベースに直接書き込まず、環境変数や外部設定ファイル（YAML/JSON）で管理してください。

---

必要であれば、README に記載する API 仕様のテンプレートやベースクラスのサンプル実装を作成します。どのサブパッケージから実装を始めたいか教えてください。