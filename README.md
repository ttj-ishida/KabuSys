# KabuSys

日本株自動売買システム（KabuSys）の軽量なベースパッケージです。  
このリポジトリは、データ取得、売買戦略、注文実行、監視の4つの主要モジュールで構成される設計骨格を提供します。現時点ではモジュールはパッケージ化されていますが、個別機能は未実装のため、拡張して利用してください。

バージョン: 0.1.0

---

## 概要

KabuSysは日本株の自動売買システム開発を支援するための骨組みを提供します。  
以下の責務ごとにモジュールを分離しており、各モジュールを実装・拡張することで、フル機能の自動売買システムが構築できます。

- data: 市場データの取得・整形
- strategy: 売買戦略（シグナル生成）
- execution: 注文送信やリスク管理
- monitoring: ログ・メトリクス・状態監視

このREADMEは、プロジェクトの概要、機能、セットアップ、使い方、ディレクトリ構成および拡張のヒントをまとめたものです。

---

## 機能一覧（想定／拡張ポイント）

現行のパッケージはモジュール構造のみを提供します。以下は実装を想定した機能リストです。

- data
  - 株価（ティッカー、板情報、約定履歴など）の取得
  - CSV/DBへの保存・読み込み
  - データの前処理（リサンプリング、欠損処理、テクニカル指標計算）
- strategy
  - シグナル生成（例: 移動平均クロス、RSI、ボラティリティブレイクアウト）
  - ポジション管理ロジック（エントリー/エグジット条件）
  - バックテストの簡易サポート（履歴データを用いた評価）
- execution
  - 注文APIクライアント（約定確認、注文取消）
  - スリッページ・最大ロット・注文タイプ管理
  - リスク制御・資金管理
- monitoring
  - ロギング、アラート（メール、Slack、Webhook等）
  - トレード/戦略のメトリクス収集
  - 稼働状況のヘルスチェック

---

## セットアップ手順

推奨環境
- Python 3.8+
- 仮想環境（venv、conda 等）

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境の作成と有効化（例: venv）
   - macOS / Linux
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell)
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージのインストール  
   このテンプレートでは依存ファイルが含まれていません。必要なパッケージをrequirements.txtに記載している場合は以下を実行してください。
   ```
   pip install -r requirements.txt
   ```
   または、開発用にプロジェクトを編集可能インストールする場合:
   - プロジェクトが packaging (pyproject.toml / setup.py) を備えているなら:
     ```
     pip install -e .
     ```
   - packaging が無い場合は、開発中は PYTHONPATH を通す方法で利用できます:
     - macOS / Linux:
       ```
       export PYTHONPATH=$(pwd)/src:$PYTHONPATH
       ```
     - Windows (PowerShell):
       ```
       $env:PYTHONPATH = (Resolve-Path .\src).Path + ";" + $env:PYTHONPATH
       ```

4. （任意）APIキーや設定の準備  
   実際の注文やデータ取得を行う場合は、取引所やデータプロバイダのAPIキー等を環境変数や設定ファイル（例: config.yaml）で管理してください。

---

## 使い方（例）

現在のパッケージはモジュールのスケルトンのみを提供します。下記は拡張実装を行った想定での利用例です。

基本的なインポート／バージョン確認:
```python
from kabusys import __version__
print("KabuSys version:", __version__)

from kabusys import data, strategy, execution, monitoring
```

想定されるワークフロー（擬似コード）:
```python
# 1. データ取得
prices = data.fetch_prices(ticker="7203", start="2023-01-01", end="2023-03-31")

# 2. シグナル生成
signals = strategy.generate_signals(prices)

# 3. 注文実行（シグナルに従う）
for sig in signals:
    if sig.action == "buy":
        execution.place_order(ticker=sig.ticker, side="BUY", quantity=sig.qty)
    elif sig.action == "sell":
        execution.place_order(ticker=sig.ticker, side="SELL", quantity=sig.qty)

# 4. 監視・ログ
monitoring.log_trade(signals)
monitoring.check_health()
```

注意:
- 上記の関数（fetch_prices, generate_signals, place_order, log_trade, check_health）はテンプレート段階では未実装です。各モジュール内に実装を追加してください。
- 実際の注文機能を実装する際は、注文のテスト環境（ペーパー取引）や十分なエラーハンドリングを必ず導入してください。

推奨される関数シグネチャの例（実装ガイド）:
- data.fetch_prices(ticker: str, start: str, end: str) -> pandas.DataFrame
- strategy.generate_signals(df: pd.DataFrame) -> List[Signal]
- execution.place_order(ticker: str, side: str, quantity: int, order_type: str = "MARKET") -> OrderResult
- monitoring.log_trade(trade: Trade) -> None

---

## ディレクトリ構成

現在の構成（最小限）:
```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py          # パッケージ定義、__version__
│     ├─ data/
│     │  └─ __init__.py       # データ取得モジュール（拡張）
│     ├─ strategy/
│     │  └─ __init__.py       # 戦略モジュール（拡張）
│     ├─ execution/
│     │  └─ __init__.py       # 注文実行モジュール（拡張）
│     └─ monitoring/
│        └─ __init__.py       # 監視・ロギングモジュール（拡張）
└─ README.md
```

各フォルダ内にサブモジュール（client.py, utils.py, models.py など）を追加して実装を進めることを推奨します。

---

## 開発・拡張のヒント

- 設計
  - 各モジュールは単一責務（Single Responsibility）を保つ。
  - 明確なインターフェース（関数/クラス）を定義し、テストを書きやすくする。
- テスト
  - ユニットテストと統合テストを用意する（モックで外部APIを置き換える）。
- セキュリティ
  - APIキーはリポジトリに含めない。環境変数やシークレットマネージャを使用。
- ロギング／監視
  - 重要なイベント（注文送信、約定、エラー）を記録する。
  - Slackやメール通知などのアラートを実装する。
- リスク管理
  - 1トレードあたりの最大ドローダウン、ポジションサイズ制限、サーキットブレーカーなどを実装する。

---

## 貢献方法

1. Issueを立てる（機能提案・バグ報告）
2. Forkしてブランチを作成
3. 実装・ユニットテスト追加
4. Pull Requestを送る

---

## 最後に

このリポジトリは自動売買システム構築のテンプレートです。実運用に用いる前に十分な検証、法令・取引所ルールの確認、リスク管理を行ってください。具体的な実装やサンプル実装の追加が必要であれば、ご希望に応じて README やテンプレートコードを拡張します。