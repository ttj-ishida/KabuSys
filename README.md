# KabuSys

日本株自動売買システムの雛形パッケージです。  
モジュールは「データ取得 (data)」「ストラテジ (strategy)」「注文実行 (execution)」「監視 (monitoring)」の4つに分かれており、それぞれを実装して自動売買システムを構築できるようにしています。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株向けの自動売買システムの骨組み（テンプレート）です。  
主要な関心事を分離したモジュール構成により、データ取得方法（API/CSV等）、トレード戦略、注文実行ロジック、監視／ロギング機能を独立して実装・テストできます。

主な設計方針:
- モジュール化して責務を分離
- 拡張しやすいインターフェース（各サブパッケージに実装を追加）
- 実運用前にローカルで検証しやすい構成

---

## 機能一覧

現状（ベース）で提供される機能:
- パッケージ構造の雛形（data, strategy, execution, monitoring）
- パッケージバージョン管理（`kabusys.__version__`）
- 開発者が各機能を実装するための出発点

将来的に実装が想定される機能例:
- 市場データ取得（リアルタイム／過去データ）
- 複数戦略の登録とシミュレーション（バックテスト）
- 注文送信（取引所API連携、注文管理、約定確認）
- 監視ダッシュボード／アラート（ログ、メール・Slack通知）
- リスク管理（ポジション管理、証拠金監視）

---

## セットアップ手順

開発・実行するための基本的な手順を示します。プロジェクトルートが次のような構成になっていることを想定してください:

- プロジェクトルート/
  - src/
    - kabusys/
      - __init__.py
      - data/
      - strategy/
      - execution/
      - monitoring/
  - README.md
  - （任意）pyproject.toml / setup.cfg

1. Python 環境の準備
   - 推奨: Python 3.8 以上
   - 仮想環境を作成して有効化
     - macOS / Linux:
       - python -m venv .venv
       - source .venv/bin/activate
     - Windows (PowerShell):
       - python -m venv .venv
       - .\.venv\Scripts\Activate.ps1

2. 依存パッケージのインストール
   - 依存が明示されていない場合は必要に応じて追加してください（例: requests, pandas, numpy 等）
   - 例:
     - pip install requests pandas numpy

3. 開発時の利用方法（2通り）
   - a) パッケージとしてインストールできる場合（pyproject.toml / setup.cfg がある場合）:
     - pip install -e .
   - b) まだパッケージ設定がない場合（簡易的に実行する方法）:
     - 環境変数 PYTHONPATH を設定して src を追加
       - macOS / Linux:
         - export PYTHONPATH=$(pwd)/src:$PYTHONPATH
       - Windows (PowerShell):
         - $env:PYTHONPATH = "$(Get-Location)\src;$env:PYTHONPATH"
     - これで Python から `import kabusys` が可能になります。

---

## 使い方（基本例）

パッケージの読み込みとバージョン確認例:

```python
import kabusys

print(kabusys.__version__)  # 例: "0.1.0"

# サブパッケージ群をインポート（実装を追加して利用）
from kabusys import data, strategy, execution, monitoring
```

モジュールに機能を実装する際の例（雛形）:

- data: データソース抽象化。例えば API クライアントや CSV ローダーを実装。
  - 例: data/tokyo_stock_api.py にクラス TokyoStockAPIClient を追加し、OHLC データ取得メソッドを提供

- strategy: 戦略のインターフェースや実装を定義。
  - 例: strategy/base.py に Strategy クラス（generate_signals 等）を定義し、strategy/simple_mean_reversion.py で実装

- execution: 注文の送信・管理を実装。
  - 例: execution/kabu_api.py に OrderExecutor クラスを作成し、注文送信・約定確認ロジックを追加

- monitoring: ロギングやアラート機能を実装。
  - 例: monitoring/logger.py、monitoring/alert.py を作成してログ収集やSlack通知を行う

簡単なワークフロー例（擬似コード）:

```python
# 1. データ取得
prices = data.TokyoStockAPIClient().get_ohlc("7203")  # 銘柄コード: 例としてトヨタ

# 2. シグナル生成
sig = strategy.SimpleMeanReversion().generate_signal(prices)

# 3. 注文実行
executor = execution.OrderExecutor()
if sig == "BUY":
    executor.place_order("7203", side="BUY", qty=100)

# 4. 監視・ログ
monitoring.Logger().info("Order placed for 7203")
```

（上記は実装例です。各モジュールに実装を追加してから利用してください）

---

## ディレクトリ構成

現状の最小構成:

- src/
  - kabusys/
    - __init__.py            # パッケージ定義、バージョン情報
    - data/
      - __init__.py
      # データ取得に関する実装を追加（例: tokyo_api.py, loader.py）
    - strategy/
      - __init__.py
      # 戦略の実装を追加（例: base.py, mean_reversion.py）
    - execution/
      - __init__.py
      # 注文実行ロジックを追加（例: executor.py, api_adapter.py）
    - monitoring/
      - __init__.py
      # ログ・アラート機能を追加（例: logger.py, alert.py）

プロジェクトルートに以下ファイルを追加すると便利です:
- pyproject.toml / setup.cfg / setup.py（パッケージ配布・インストール用）
- requirements.txt（依存管理）
- tests/（ユニットテスト）

---

## 開発・貢献

- 新しい機能や修正は各サブパッケージ内にモジュールを追加して実装してください。
- ユニットテストを作成し、CI（例: GitHub Actions）で実行することを推奨します。
- コードスタイル: black, flake8 等を導入すると統一しやすいです。

---

## 注意事項

- 本リポジトリは雛形です。実際の自動売買を行う前に十分なデバッグ、バックテスト、セキュリティ確認（API キーの管理、注文失敗時の回復処理等）を行ってください。
- 取引にはリスクが伴います。実運用は自己責任で行ってください。

---

必要であれば、README に具体的な実装例（サンプル戦略、API アダプタ、テストコード）を追加して作成します。どの部分のサンプルを優先的に入れたいか教えてください。