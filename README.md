# KabuSys

日本株自動売買システムの骨組み（スケルトン）パッケージです。  
このリポジトリは、データ取得、売買戦略、注文実行、監視・ロギングを分離したモジュール構成を提供します。各モジュールは拡張可能なインターフェースを想定しており、実際の取引ロジック・API連携を実装していくための出発点となります。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- モジュール分割されたパッケージ構成
  - data: 市場データの取得／保存用インターフェース
  - strategy: 売買戦略の実装場所
  - execution: 注文発行（ブローカーAPIとの接続）を行う場所
  - monitoring: ログ、アラート、稼働監視のための仕組み
- 軽量なスケルトンで、用途に合わせて拡張しやすい構造
- pip でのインストールや開発環境での編集に対応（ソース配布）

※ 現状はパッケージの骨組みのみで、具体的なデータ取得や注文実行の実装は含みません。実装はユーザー側で追加してください。

---

## 前提条件

- Python 3.8+
- git（ソースからインストールする場合）
- 実運用時は各ブローカー（kabuステーションなど）のAPIキーや接続情報が必要（実装に依存）

（必要に応じて仮想環境を使うことを推奨します）

---

## セットアップ手順

1. リポジトリをクローンする（ローカル開発用）
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成・有効化（例: venv）
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

3. パッケージを開発モードでインストール
   ```
   pip install -e .
   ```
   もしくは、配布パッケージがある場合は `pip install kabusys`（配布されていれば）

4. 依存ライブラリがある場合は、requirements.txt を追加している想定であれば
   ```
   pip install -r requirements.txt
   ```
   （現状のスケルトンには依存ファイルは含まれていません）

5. 必要に応じて環境変数を設定（実際のAPI実装を行う場合）
   - 例:
     - KABU_API_KEY
     - KABU_API_SECRET
     - KABU_API_ENDPOINT

---

## 使い方（基本）

パッケージをインポートしてバージョンを確認する簡単な例:

```python
import kabusys

print(kabusys.__version__)  # 0.1.0
```

モジュールの拡張例（実装例・ベストプラクティス）

- data モジュール: データ取得クラスの雛形
```python
# src/kabusys/data/connector.py
class DataConnector:
    def __init__(self, config):
        self.config = config

    def fetch_price(self, symbol, interval):
        """市場データを取得して返す（実装してください）"""
        raise NotImplementedError
```

- strategy モジュール: 戦略クラスの雛形
```python
# src/kabusys/strategy/simple_strategy.py
class Strategy:
    def __init__(self, params):
        self.params = params

    def on_market(self, market_data):
        """市場データを受け取ってシグナルを返す（買い/売り/何もしない）"""
        raise NotImplementedError
```

- execution モジュール: 注文実行エンジンの雛形
```python
# src/kabusys/execution/executor.py
class ExecutionEngine:
    def __init__(self, api_client):
        self.api_client = api_client

    def send_order(self, order):
        """注文をブローカーAPIへ送信（実装してください）"""
        raise NotImplementedError
```

- monitoring モジュール: ログ／監視の例
```python
# src/kabusys/monitoring/monitor.py
class Monitor:
    def __init__(self):
        pass

    def alert(self, message):
        """アラート送信（メール/Slack/監視ダッシュボードなど）"""
        raise NotImplementedError
```

これらを組み合わせて、データ取得 → 戦略判定 → 注文実行 → 監視 というワークフローを構築します。

---

## ディレクトリ構成

現在のコードベースのファイル構成は次の通りです。

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py         # パッケージ定義、バージョン情報
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
├─ setup.py / pyproject.toml   # （プロジェクトに合わせて追加）
└─ README.md                   # このファイル
```

注: 各サブパッケージは現在空の初期化ファイルのみを持ち、具体的な実装は含まれていません。用途に応じてファイルを追加して実装してください。

---

## 開発のヒント / 拡張ガイド

- まずはローカル環境でモック（ダミー）データやモックAPIクライアントを実装して、戦略ロジックと注文フローの検証を行ってください。
- 実運用前に十分なバックテストとペーパートレードで挙動確認を行うことを強く推奨します。
- 注文執行部分は誤発注のリスクが高いため、以下の対策を検討してください:
  - 注文前に安全チェック（最大発注額、ポジションリミットなど）を実装
  - 発注の二重確認（サンドボックス環境や手動承認フロー）
  - ロギングとリカバリ戦略（失敗時のリトライ、履歴保存）
- 監視はリアルタイムの稼働状況や異常検知に重要です。アラート通知（Slack/メール）やメトリクス収集（Prometheus 等）を組み込んでください。

---

## ライセンス / 責任

本プロジェクトはリスクのある金融ソフトウェアのため、実運用に使用する前に十分な監査とテストを行ってください。実運用での損失に関して本リポジトリの作成者は責任を負いません。ライセンスはリポジトリに明記してください（例: MIT等）。

---

この README は現状のパッケージ構成（スケルトン）に基づくドキュメントです。具体的な実装やAPI仕様が追加されたら、README を更新して使い方や設定方法を詳述してください。