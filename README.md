# KabuSys

KabuSys は日本株の自動売買システムのベースとなる Python パッケージです。  
このリポジトリは最小限のパッケージ構成（データ取得、ストラテジ、注文実行、監視）のスケルトンを提供し、開発者が各モジュールを拡張して自動売買システムを構築できるように設計されています。

---

## 主な内容（概要）
- パッケージ名: `kabusys`
- バージョン（初期）: `0.1.0`（`src/kabusys/__init__.py`）
- モジュール構成:
  - `data` — 市場データの取得・整形
  - `strategy` — 売買ロジック（シグナル生成）
  - `execution` — 注文送信・約定管理
  - `monitoring` — ロギング、メトリクス、通知

このリポジトリはあくまで骨組み（テンプレート）を提供します。実際の注文送信 API やデータソースは各自で実装・接続してください（例: 証券会社 API、CSV/データベース、バックテスト用データなど）。

---

## 機能一覧
- パッケージ基盤（名前空間とバージョン管理）
- サブパッケージ分割（`data`, `strategy`, `execution`, `monitoring`）
- 開発者が拡張しやすいシンプルな構造

※ 現状は実装の雛形のみで、個別機能（実際の注文送信、データ取得等）は含まれていません。プロジェクト用途に合わせて実装を追加してください。

---

## 前提・要件
- Python 3.8 以上（推奨）
- 任意: 仮想環境（venv, virtualenv, conda など）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリ URL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成（任意だが推奨）
   ```
   python -m venv .venv
   # Unix / macOS
   source .venv/bin/activate
   # Windows (PowerShell)
   .\.venv\Scripts\Activate.ps1
   ```

3. pip を最新に
   ```
   pip install --upgrade pip
   ```

4. 開発中のパッケージを編集可能モードでインストール
   - パッケージ化のための `setup.py` や `pyproject.toml` を用意している場合:
     ```
     pip install -e .
     ```
   - まだパッケージ化していない場合は、実行時に `src` を PYTHONPATH に含める方法:
     - Unix/macOS:
       ```
       export PYTHONPATH=$(pwd)/src:$PYTHONPATH
       ```
     - Windows (PowerShell):
       ```
       $env:PYTHONPATH = "$(Resolve-Path .\src)"; $env:PYTHONPATH
       ```

5. 必要な依存パッケージを追加する場合は `requirements.txt` を用意し、以下でインストールしてください:
   ```
   pip install -r requirements.txt
   ```

---

## 使い方（基本例・拡張方法）
現状はモジュールの骨組みのみのため、利用するには各サブパッケージに実装を追加します。以下は拡張のための簡単なテンプレート例です。

- バージョン確認（インストールまたは PYTHONPATH を通している前提）
```python
import kabusys
print(kabusys.__version__)  # 0.1.0
```

- ストラテジ/実行モジュール雛形
  - src/kabusys/strategy/sample_strategy.py
    ```python
    class SampleStrategy:
        def __init__(self, params=None):
            self.params = params or {}

        def generate_signals(self, market_data):
            """
            market_data: 任意形式（DataFrame や dict など）
            戻り値: 注文シグナルのリスト（各要素は注文情報を表す dict 等）
            """
            signals = []
            # シグナル生成ロジックを実装
            return signals
    ```
  - src/kabusys/execution/sample_executor.py
    ```python
    class SampleExecutor:
        def __init__(self, api_client=None):
            self.api_client = api_client  # 証券会社 API クライアント等

        def send_orders(self, orders):
            """
            orders: ストラテジから受け取った注文リスト
            ここで実際の注文送信/発注制御を行う
            """
            for o in orders:
                # API 呼び出し等を行う
                pass
    ```

- 簡単な統合例
```python
from kabusys.strategy.sample_strategy import SampleStrategy
from kabusys.execution.sample_executor import SampleExecutor

# 市場データ（例）
market_data = {...}

strategy = SampleStrategy(params={'ma_period': 25})
signals = strategy.generate_signals(market_data)

executor = SampleExecutor(api_client=...)
executor.send_orders(signals)
```

- 監視・ロギングの追加
  - `kabusys.monitoring` にログ収集、メトリクス送信、通知（メール/Slack 等）のユーティリティを実装して利用します。

---

## 開発上のヒント
- 各サブパッケージ（data, strategy, execution, monitoring）ごとにテストを用意すると保守しやすくなります。
- 実際の注文を行う前に、モックやサンドボックス環境で必ず動作検証を行ってください。
- 銘柄・発注制限・レート制限等のリスク管理ロジックを execution 側で強化してください。
- ログは十分に取り、失敗時のリカバリや手動停止フラグを用意しておきましょう。

---

## ディレクトリ構成
現在のリポジトリは最小構成のスケルトンです。実際のファイルは以下のようになっています。

- src/
  - kabusys/
    - __init__.py              # パッケージ初期化・バージョン定義
    - data/
      - __init__.py
      # （ここにデータ取得・整形用のモジュールを追加）
    - strategy/
      - __init__.py
      # （ここにストラテジ実装を追加）
    - execution/
      - __init__.py
      # （ここに注文実行ロジックを追加）
    - monitoring/
      - __init__.py
      # （ここに監視・通知ロジックを追加）

上記の各ディレクトリは現状 empty の __init__.py のみ含んでおり、目的に応じてモジュールを追加してください。

---

## 貢献
- バグ報告、機能提案、プルリクエスト歓迎します。
- 変更を加える際は、可能なら単体テスト・ドキュメントを付けてください。

---

必要であれば、README にサンプルワークフロー（バックテストの流れ、運用時の注意点、証券会社 API 接続例など）を追加で作成します。どの部分の例を深掘りしたいか教えてください。