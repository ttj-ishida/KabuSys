# KabuSys

日本株の自動売買システムの骨組み（テンプレート）です。  
モジュール分割（データ収集、売買戦略、注文実行、監視）を想定したパッケージ構成になっており、実運用向けの機能を追加して拡張していくことを想定しています。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買を目的とした Python パッケージの雛形です。  
各責務を分離したサブパッケージを持ち、以下の主要コンポーネントを提供・拡張できます。

- データ収集（market data / historical）
- 売買戦略（シグナル生成）
- 注文実行（ブローカー/API 連携）
- 監視・ロギング（稼働状況、通知）

現在はパッケージ構成のみを用意しており、各モジュールの具体実装はプロジェクトごとに追加してください。

---

## 機能一覧（想定）

- market data の取得・キャッシュ（拡張）
- 戦略モジュールによる売買シグナル生成
- 注文発注・約定管理（ブローカーAPIラッパー）
- 稼働監視・ログ出力・アラート（メール/Slack 等へ通知）
- バックテスト基盤（将来的な拡張）

（注）本リポジトリは雛形のため、上記機能は実装例を追加していく必要があります。

---

## 要件

- Python 3.8+
- pip

（実際に使うライブラリ（requests、pandas、websocket-client など）は実装に応じて requirements.txt に追加してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成・有効化
   - macOS / Linux
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell)
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 開発インストール（編集を反映させながら使う場合）
   ```
   pip install -e .
   ```

4. 依存パッケージ（必要に応じて）
   ```
   pip install <必要なライブラリ>
   ```

5. API キー等の設定  
   ブローカーやデータプロバイダと接続する場合は API キー等の設定が必要です。環境変数または設定ファイルを利用してください（例）：
   - 環境変数
     - KABUSYS_API_KEY
     - KABUSYS_API_SECRET
   - 設定ファイル（config.json 等）
     ```json
     {
       "api_key": "あなたのAPIキー",
       "api_secret": "あなたのシークレット"
     }
     ```

---

## 使い方（サンプル）

現在はパッケージの骨組みのみ提供します。以下は利用例（各モジュールを実装した場合の典型的な流れ）です。

```python
import kabusys

print("KabuSys version:", kabusys.__version__)

# 仮に各モジュールにクラスを実装した場合の例
from kabusys.data import DataClient      # 実装を追加
from kabusys.strategy import Strategy    # 実装を追加
from kabusys.execution import Executor   # 実装を追加
from kabusys.monitoring import Monitor   # 実装を追加

# クライアント初期化（実装に応じて）
data_client = DataClient(api_key="...")
strategy = Strategy(params={})
executor = Executor(api_key="...")
monitor = Monitor()

# メインループ（概念例）
while True:
    market = data_client.fetch_latest("7203")      # 銘柄コード例: トヨタ
    signal = strategy.generate_signal(market)
    if signal == "BUY":
        executor.place_order(symbol="7203", side="BUY", size=100)
    elif signal == "SELL":
        executor.place_order(symbol="7203", side="SELL", size=100)
    monitor.record(market, signal)
    # 適切な待機/スケジューリングを行う
```

上記はあくまでサンプルです。実際にはエラーハンドリング、リトライ、レート制限対策、注文の確認・管理、バックテスト機能などを実装してください。

---

## ディレクトリ構成

プロジェクトの現状ディレクトリ構成（主要ファイルのみ）:

- src/
  - kabusys/
    - __init__.py          (バージョンと __all__ 設定)
    - data/
      - __init__.py        (データ取得モジュール用)
    - strategy/
      - __init__.py        (戦略モジュール用)
    - execution/
      - __init__.py        (注文実行モジュール用)
    - monitoring/
      - __init__.py        (監視・ロギング用)

README.md、setup.cfg / pyproject.toml、requirements.txt、LICENSE などの管理ファイルはプロジェクトルートに追加してください。

---

## 開発・貢献

- 新しい機能や修正はブランチを切ってプルリクエストで提出してください。
- 重大な変更を加える場合は事前に Issue を立てて議論してください。
- 単体テスト、静的解析（flake8/black/isort 等）の導入を推奨します。

---

## 注意事項

- 自動売買は資金リスクを伴います。実運用前に十分な検証（バックテスト、ペーパートレード）を行ってください。
- ブローカーの API 利用規約、金融商品取引法等の法規制に従ってください。

---

必要であれば、サンプル実装（DataClient/Strategy/Executor/Monitor のテンプレート）や CI 設定、バックテストの雛形を追加した README の拡張版を作成します。どの部分を具体的に実装したいか教えてください。