# KabuSys

日本株自動売買システム（プロジェクト骨組み）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのためのパッケージ構成（スケルトン）です。  
主要な責務を分割したモジュール群を提供し、データ取得（data）、売買戦略（strategy）、注文実行（execution）、監視・ログ（monitoring）を中心に拡張していくことを意図しています。

このリポジトリはフレームワーク（骨組み）であり、具体的な API 実装や取引ロジックはユーザが実装して利用します。

---

## 機能一覧

現状（0.1.0）はパッケージ構成のみを提供します。将来的に想定している主な機能は以下です。

- data: 市場データ取得・整形（板情報、約定履歴、OHLC 等）
- strategy: 売買戦略の定義・シミュレーション・バックテスト
- execution: 注文管理（成行・指値・取消し）、注文状態の追跡
- monitoring: 実行ログ、アラート、パフォーマンス指標の収集・可視化

※ 現在のコードベースはモジュールのプレースホルダのみを含みます。実際の機能は各モジュールに実装してください。

---

## セットアップ手順

このプロジェクトをローカルで利用・開発するための基本手順を示します。

前提
- Python 3.8 以上を推奨（プロジェクトの要件に応じて変更してください）

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境の作成（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. インストール（編集・開発する場合は -e オプション）
   プロジェクトルートに `setup.py` や `pyproject.toml` がある場合:
   ```
   pip install -e .
   ```
   まだパッケージ化していない場合は、直接 PYTHONPATH を通すか、src をパスに含めて import できます。

4. 依存関係
   - 現状サンプルコードに外部依存はありません。実際に API クライアントやデータ処理ライブラリを追加する際は `requirements.txt` を作成してください。

---

## 使い方

基本的なパッケージの利用例と、各モジュールを拡張する際の雛形例を示します。

- パッケージのバージョン確認・インポート
```python
import kabusys
print(kabusys.__version__)  # "0.1.0"
```

- サブモジュールのインポート（現状は空モジュール）
```python
from kabusys import data, strategy, execution, monitoring
```

- strategy に簡単な戦略クラスを実装する例（雛形）
```python
# src/kabusys/strategy/simple_strategy.py
class SimpleStrategy:
    def __init__(self, config):
        self.config = config

    def on_market_data(self, tick):
        # tick を受け取って売買判断を行う
        # 戻り値として 'buy'/'sell'/None などを返す設計にする想定
        return None
```

- execution に注文実行インターフェースを作る例（雛形）
```python
# src/kabusys/execution/client.py
class ExecutionClient:
    def __init__(self, api_key=None):
        self.api_key = api_key

    def send_order(self, symbol, side, qty, price=None):
        # 実際の取引所/API 呼び出しを実装
        raise NotImplementedError

    def cancel_order(self, order_id):
        raise NotImplementedError
```

- 実行フローの概念例
  1. data モジュールで市場データを取得
  2. strategy モジュールでデータを元に売買判断
  3. execution モジュールで注文を送信
  4. monitoring モジュールでログや指標を収集・通知

---

## ディレクトリ構成

現在の最小構成（src 配下）:

- src/
  - kabusys/
    - __init__.py               (パッケージ初期化、__version__ 定義)
    - data/
      - __init__.py             (データ関連モジュール群)
    - strategy/
      - __init__.py             (戦略関連モジュール群)
    - execution/
      - __init__.py             (注文実行関連モジュール群)
    - monitoring/
      - __init__.py             (監視・ログ関連モジュール群)

実際のプロジェクトでは各サブパッケージに複数のモジュール（API クライアント、モデル、ユーティリティ等）を追加していきます。

例（拡張時の想定）
- src/kabusys/data/api.py
- src/kabusys/data/loader.py
- src/kabusys/strategy/base.py
- src/kabusys/execution/client.py
- src/kabusys/monitoring/logger.py

---

## 今後の拡張案（参考）

- Kabuステーション / 各証券会社API のクライアント実装
- 戦略のバックテスト機能
- プロセス監視・リトライ・フォルトトレランス
- Web UI / ダッシュボードによる可視化とアラート

---

## ライセンス / 貢献

- ライセンス情報・コントリビューション方針はリポジトリに合わせて追記してください。  
- セキュリティや実際の資金を扱う実装は十分なテスト・レビュー・リスク管理のもとで行ってください。

---

必要があれば、README にサンプル実装や CI / テストの設定例、依存パッケージ一覧を追加して拡張します。どのような使用例（例: 実際の API 統合やバックテスト機能）を優先したいか教えてください。