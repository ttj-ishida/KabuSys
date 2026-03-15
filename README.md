# KabuSys

日本株向けの自動売買システムのひな形パッケージです。  
このリポジトリは、データ取得、取引戦略、注文実行、監視の役割を分離したモジュール構成を採用しており、任意のアルゴリズムや外部APIに接続して拡張できるように設計されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株の自動売買システム構築のための最小限のフレームワークです。主に以下の機能をモジュール単位で提供／拡張できるように設計されています。

- 市場データの取得・管理（data）
- 売買ロジック・戦略の実装（strategy）
- 注文の送信・約定管理（execution）
- 状態監視・アラート（monitoring）

現状はパッケージの骨組みのみを提供しており、各モジュール内の実装はプロジェクト固有に実装して使うことを前提としています。

---

## 機能一覧（想定）

- データ取得
  - 株価（時系列）取得
  - 銘柄情報の取得
- 戦略
  - シグナル生成（例：移動平均クロス、ボラティリティ等）
  - リスク・マネジメント（最大ポジション等）
- 実行
  - 注文送信（成行・指値）
  - 注文状態の管理（約定、取消し等）
- 監視
  - ログ出力
  - アラート（メール／Slack等への通知）

※ 実際の取引API（例：カブドットコムAPI等）との接続は実装者が行ってください。

---

## 要件

- Python 3.8+
- （実装に応じて）各種APIクライアントライブラリ、HTTPクライアント、pandas 等

---

## インストール（開発用）

リポジトリのルートに setup.py / pyproject.toml がある前提での開発インストール例：

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 開発インストール
   - pip install -e .

※ 本テンプレートは src/ 配下にパッケージが置かれています。setuptools/poetry の設定はプロジェクトに応じて追加してください。

---

## セットアップ（設定・認証）

自動売買を行う場合は、取引所または証券会社のAPIキーや認証情報が必要です。機密情報は環境変数や外部設定ファイル（例：YAML, JSON）に格納し、ソース管理には含めないようにしてください。

例（環境変数）:
- KABU_API_KEY
- KABU_API_SECRET
- KABU_ACCOUNT_ID

監視や通知を行う場合は、Slack webhook URL やメールサーバー情報なども同様に設定します。

---

## 使い方（基本例）

このリポジトリは実装の雛形のため、まずは各モジュールを実装して使えるようにします。最小限の確認例を示します。

Python REPL / スクリプトでの確認例:

```python
import kabusys

# バージョン表示
print(kabusys.__version__)

# モジュールの参照（実装を追加してから利用）
import kabusys.data as data
import kabusys.strategy as strategy
import kabusys.execution as execution
import kabusys.monitoring as monitoring

# 各モジュールに実装を追加し、例えば以下のように利用します（擬似コード）
# data_client = data.Client(api_key=os.getenv("KABU_API_KEY"))
# price = data_client.get_price("7203")  # 銘柄コード
# signal = strategy.SimpleMovingAverage().generate(price_history)
# order = execution.Client().send_order(symbol="7203", side="BUY", size=100, price=None)
# monitoring.notify("order sent", order)
```

実際の利用にあたっては、各モジュール内にクラスや関数を追加して、APIクライアント、戦略ロジック、注文管理を実装してください。

---

## ディレクトリ構成

プロジェクトは以下のような構成です（抜粋）:

- src/
  - kabusys/
    - __init__.py         (パッケージ初期化、バージョン定義)
    - data/
      - __init__.py       (データ取得用モジュール)
      - ...              (データクライアント等を実装)
    - strategy/
      - __init__.py       (戦略実装用モジュール)
      - ...              (戦略クラス等を実装)
    - execution/
      - __init__.py       (注文実行用モジュール)
      - ...              (APIラッパー、注文ロジック等を実装)
    - monitoring/
      - __init__.py       (監視・通知モジュール)
      - ...              (ログ、アラート用実装)
- setup.py or pyproject.toml (任意)
- README.md

現状のファイル（本テンプレートに含まれるもの）:
- src/kabusys/__init__.py
- src/kabusys/data/__init__.py
- src/kabusys/strategy/__init__.py
- src/kabusys/execution/__init__.py
- src/kabusys/monitoring/__init__.py

---

## 開発・拡張ガイド

- モジュール分割の意図
  - data: APIやファイルからのデータ取得／キャッシュ
  - strategy: シグナル生成、エントリー・エグジット判定
  - execution: 注文の送信、履歴管理、注文再試行
  - monitoring: ログ、メトリクス収集、アラート

- テスト
  - 各モジュールはユニットテストを書いておくことを推奨します（pytest 等）。

- セーフティ
  - 本番での稼働前にバックテスト、ペーパートレードを必ず実施してください。
  - 取引APIのレート制限やエラー処理（再試行、バックオフ）を実装してください。
  - 送金・APIキー等の管理は厳重に行ってください。

---

## 最後に

このリポジトリは自動売買システムを構築するための骨組みです。実際の運用に用いる際は、各モジュールに十分な実装、テスト、安全対策を行った上で利用してください。実装や拡張に関する具体的な要望があれば、目的（例：利用するブローカー、戦略の種類、監視要件）を教えてください。より詳細な実装例やテンプレートを用意します。