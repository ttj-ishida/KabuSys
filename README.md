# KabuSys

日本株向けの自動売買システムの骨組み（KabuSys）。  
このリポジトリはモジュール構成のみを持つシンプルなパッケージで、データ取得、売買戦略、注文実行、監視の4つの役割に分かれた拡張可能なアーキテクチャを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株（kabu）を対象とした自動売買システムのベースとなるライブラリです。  
各機能（データ取得・戦略・実行・監視）をモジュール化しており、実装を差し替えたり拡張したりして独自の自動売買ロジックを構築できます。

対象ユーザー:
- 自動売買のプロトタイプを作成したい開発者
- 戦略/実行部分をカスタム実装して運用したい方
- 教育目的でシステム構成を学びたい方

---

## 機能一覧（設計上の役割）

- data: 市場データ（板情報・約定履歴・終値など）の取得・加工を行うモジュール
- strategy: 取得したデータを元に売買シグナルやポートフォリオを決めるロジックを実装するモジュール
- execution: 発注・キャンセル・注文状態の管理など、取引所やブローカーとやり取りするモジュール
- monitoring: 稼働状況のログ、アラート、パフォーマンス監視を担当するモジュール

※ 現状はモジュール構成のみで、実際の実装（クラス・関数）は含まれていません。各モジュールに独自実装を追加して利用します。

---

## セットアップ手順

想定: Python 3.8 以上

1. リポジトリをクローン（既にローカルにある場合は不要）
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境を作成・有効化（推奨）
   - macOS / Linux:
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. パッケージをインストール（開発中は editable install が便利）
   ```
   pip install -e src
   ```
   依存関係がある場合は `requirements.txt` をプロジェクトに追加し、次のようにインストールしてください:
   ```
   pip install -r requirements.txt
   ```

4. 環境変数や認証情報の設定  
   実際の取引APIを使う場合は API キーやシークレットを環境変数等で設定します。例:
   ```
   export KABUSYS_API_KEY="your_api_key_here"
   export KABUSYS_API_SECRET="your_api_secret_here"
   ```
   （Windows の場合は set / PowerShell の Set-Item を使用）

---

## 使い方（例）

現状はモジュールのスケルトンのみですが、基本的な使用イメージは以下のとおりです。

1. パッケージを読み込む（バージョン確認）
   ```python
   import kabusys
   print(kabusys.__version__)  # "0.1.0"
   ```

2. 各モジュールにクラス・関数を実装して利用する例（擬似コード）
   ```python
   # src/kabusys/data/example.py に実装した場合の利用例
   from kabusys.data import DataClient
   from kabusys.strategy import MyStrategy
   from kabusys.execution import ExecutionClient
   from kabusys.monitoring import Monitoring

   # データ取得クライアントを作成
   data_client = DataClient(api_key="xxx")

   # 戦略を初期化
   strategy = MyStrategy(params={...})

   # 実行クライアント
   exec_client = ExecutionClient(api_key="yyy")

   # 監視
   monitor = Monitoring()

   # ワークフローの例
   prices = data_client.get_latest_prices(symbol="7203")  # トヨタの銘柄コード例
   signals = strategy.generate_signals(prices)
   for s in signals:
       exec_client.place_order(s)
   monitor.record(metrics={...})
   ```

3. 実装のポイント
   - data モジュール: 取得頻度やキャッシュ、リトライなどの堅牢性を考慮
   - strategy モジュール: 再現性のためにシード管理、パラメータ記録
   - execution モジュール: 注文の一貫性（idempotency）とエラーハンドリング
   - monitoring モジュール: 障害時のアラート、取引履歴・P/L の記録

---

## ディレクトリ構成

現状の最小構成は以下のとおりです。

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py           # パッケージ初期化 (version 等)
│     ├─ data/
│     │  └─ __init__.py        # データ取得モジュール
│     ├─ strategy/
│     │  └─ __init__.py        # 戦略モジュール
│     ├─ execution/
│     │  └─ __init__.py        # 注文実行モジュール
│     └─ monitoring/
│        └─ __init__.py        # 監視モジュール
```

各サブパッケージに実装ファイル（例: clients.py, base.py, utils.py）やテストを追加していくことを想定しています。

---

## 拡張・実装のガイドライン（簡易）

- 各モジュールに共通のインターフェース（Base クラス）を作ると差し替えやテストが容易になります。
- 実運用を想定する場合、以下を検討してください:
  - ロギング（構造化ログ）
  - リトライとバックオフ戦略
  - 注文の冪等性・状態保存（永続化）
  - モニタリング/アラート（メール、Slack、PagerDuty など）
  - バックテスト用の分離（戦略の検証用データパス）

---

補足:
- このリポジトリは骨組みのみの提供です。実際の取引を行う前に、必ず十分なテストと検証を行ってください。取引には資金リスクがあります。

ご質問や具体的な実装サンプルが必要であれば、どのモジュール（data/strategy/execution/monitoring）を重点的に作りたいか教えてください。設計例やサンプル実装を提供します。