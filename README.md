# KabuSys

日本株自動売買システム（KabuSys）の軽量テンプレートです。  
モジュール分割された構成により、データ取得、売買戦略、注文実行、監視の各ロジックを独立して実装・拡張できます。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株の自動売買システムを構築するための基盤テンプレートです。  
以下の責務を持つ4つの主要パッケージで構成されています。

- data: 市場データの取得・前処理
- strategy: 売買戦略の実装
- execution: 注文送信・約定処理
- monitoring: ログ・監視・アラート

このリポジトリは最小限の骨組みを提供するため、実際の取引APIや戦略ロジックはユーザーが実装して利用します。

---

## 主な機能

- モジュール化されたプロジェクト構成（data / strategy / execution / monitoring）
- 拡張しやすいインターフェース設計（戦略・実行・監視を分離）
- 開発・テスト用の軽量テンプレート
- Python パッケージとしてインポート可能

（注）現状はテンプレートであり、取引APIとの接続や詳細な実装は含みません。

---

## セットアップ手順

前提
- Python 3.8+ を推奨
- 実際の取引を行う場合は、証券会社のAPI（kabuステーションやAPIキー等）を用意してください

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ名>
   ```

2. 仮想環境の作成（推奨）
   - Unix/macOS
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. パッケージのインストール（開発インストール）
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - 開発モードでインストール:
     ```
     pip install -e .
     ```

4. 環境変数 / 設定
   - 実際の取引APIキーやエンドポイント情報は環境変数や設定ファイルで管理してください（例: `.env`, `config.yaml`）。
   - 例:
     ```
     export KABU_API_KEY=your_api_key_here
     export KABU_API_SECRET=your_api_secret_here
     ```

---

## 使い方

本テンプレートはライブラリとしてインポートして利用します。まずはバージョン確認や各モジュールの確認から始めてください。

バージョン確認例:
```python
import kabusys
print(kabusys.__version__)  # 0.1.0
```

基本的なワークフロー（概念例）
1. data モジュールで時系列データやティックデータを取得する。
2. strategy モジュールで取得データを元に売買シグナルを生成する。
3. execution モジュールでシグナルに基づき注文を送信・管理する。
4. monitoring モジュールでログや残高、ポジションを監視し、アラートを出す。

サンプル（戦略のスケルトン）
```python
# src/kabusys/strategy/simple_strategy.py
from kabusys.data import DataClient
from kabusys.execution import ExecutionClient

class SimpleStrategy:
    def __init__(self, data_client: DataClient, exec_client: ExecutionClient):
        self.data = data_client
        self.exec = exec_client

    def on_new_bar(self, symbol: str):
        df = self.data.get_ohlcv(symbol)
        # シンプルなロジック（移動平均クロス等）
        signal = self._generate_signal(df)
        if signal == "BUY":
            self.exec.place_order(symbol=symbol, side="BUY", qty=100)
        elif signal == "SELL":
            self.exec.place_order(symbol=symbol, side="SELL", qty=100)

    def _generate_signal(self, df):
        # 実装例: 移動平均など
        return None
```

実行クライアント（概念例）
```python
# src/kabusys/execution/client.py
class ExecutionClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def place_order(self, symbol: str, side: str, qty: int):
        # ここで取引APIに注文を投げる実装を行う
        pass
```

監視（概念例）
```python
# src/kabusys/monitoring/monitor.py
class Monitor:
    def __init__(self):
        pass

    def alert_if_unexpected(self, message: str):
        # ログ出力やメール/Slack通知などを実装
        pass
```

注意点
- 実際の資金を使った売買を行う前に、バックテストやサンドボックスで十分に検証してください。
- APIレートや注文失敗時のリトライ・エラーハンドリングを必ず実装してください。

---

## ディレクトリ構成

以下は現在のプロジェクト構成（主要ファイルのみ）です。

```
src/
└─ kabusys/
   ├─ __init__.py        # パッケージメタ情報（__version__ 等）
   ├─ data/
   │  └─ __init__.py
   ├─ strategy/
   │  └─ __init__.py
   ├─ execution/
   │  └─ __init__.py
   └─ monitoring/
      └─ __init__.py
```

READMEやセットアップに関するファイル（LICENSE, requirements.txt, tests 等）があればプロジェクトルートに配置してください。

---

## 開発ガイド（簡単な推奨）

- 依存管理: requirements.txt / pyproject.toml を利用
- 型注釈とユニットテストを導入して堅牢にする（pytest 等）
- ロギング: Python の logging を使い、重要イベントは必ずログに残す
- CI/CD: テスト・品質チェックを自動化する（GitHub Actions 等）
- セキュリティ: APIキーはリポジトリに含めない（.gitignore に .env を追加）

---

このテンプレートは拡張用のベースです。実際の取引機能を追加する場合は、必ず個別の証券会社API仕様・利用規約を確認の上で実装してください。必要であれば、各モジュールのより詳細なサンプル実装やテンプレートを追加で提供できます。希望があれば教えてください。