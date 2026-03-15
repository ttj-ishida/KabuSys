# KabuSys

KabuSys は日本株の自動売買システム向けの軽量な Python パッケージの雛形です。モジュールを分割しており、データ取得、売買戦略、注文実行、監視（モニタリング）をそれぞれの責務として設計できます。本リポジトリはシステム設計の出発点（ボイラープレート）を提供します。

バージョン: 0.1.0

---

## 機能一覧

現在のリポジトリはパッケージ構成のみを提供します。各モジュールは拡張して実装することを想定しています。

- パッケージ分割（モジュール）
  - data: 市場データの取得・キャッシュ・前処理を行う場所
  - strategy: 売買戦略（シグナル生成）を実装する場所
  - execution: ブローカーや証券会社APIと連携して注文を発行する場所
  - monitoring: ログ、アラート、ダッシュボード等の監視機能を実装する場所
- パッケージメタ情報（バージョン情報）
- 拡張しやすいプロジェクト構成（開発・テスト用のベース）

注意: 現時点では各モジュールに具体実装は含まれていません。実際の売買ロジックや外部API連携はユーザが実装してください。

---

## セットアップ手順

1. リポジトリをクローン（ローカルにコピー）
   ```
   git clone <REPO_URL>
   cd <REPO_DIR>
   ```

2. Python 仮想環境の作成・有効化（例: venv）
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

3. 開発インストール
   ```
   pip install -e .
   ```
   依存パッケージがある場合は `requirements.txt` または `pyproject.toml` / `setup.cfg` に記載してインストールしてください。

4. （任意）テスト用パッケージのインストール
   ```
   pip install pytest
   ```

---

## 使い方（基本例）

パッケージは次のようにインポートして使用します。まずはバージョンの確認やモジュールの存在確認から始めます。

```python
import kabusys

print(kabusys.__version__)  # "0.1.0"
```

モジュールの雛形を拡張して使う例（擬似コード）:

- data モジュールにデータ取得クラスを実装する
  ```python
  # src/kabusys/data/market.py
  class MarketDataClient:
      def __init__(self, api_key):
          self.api_key = api_key

      def fetch_price(self, symbol):
          # 外部API呼び出しやデータ整形を実装
          return 1000.0
  ```

- strategy モジュールに戦略を実装する
  ```python
  # src/kabusys/strategy/simple.py
  class SimpleStrategy:
      def generate_signal(self, price):
          # シンプルな売買シグナルの例
          if price < 900:
              return "BUY"
          elif price > 1100:
              return "SELL"
          return "HOLD"
  ```

- execution モジュールに注文実行処理を実装する
  ```python
  # src/kabusys/execution/client.py
  class ExecutionClient:
      def place_order(self, symbol, side, qty):
          # ブローカーAPIへ注文を送信する実装
          return {"order_id": "abc123", "status": "accepted"}
  ```

- monitoring モジュールにログやアラート処理を実装する
  ```python
  # src/kabusys/monitoring/logger.py
  import logging
  logger = logging.getLogger("kabusys")
  ```

これらを組み合わせて、メインのトレードループやワークフローを実装します。

注意: 実際にプロダクションで売買を行う場合は、APIキー管理、リスク管理、フェールセーフ、注文の冪等性、ログ保存、監査、テストを必ず導入してください。

---

## ディレクトリ構成

本リポジトリの主要ファイルとフォルダは次の通りです。

- src/
  - kabusys/
    - __init__.py         : パッケージ宣言（バージョン等）
    - data/
      - __init__.py       : データ取得周りのモジュール配置場所
    - strategy/
      - __init__.py       : 戦略実装の配置場所
    - execution/
      - __init__.py       : 注文実行ロジックの配置場所
    - monitoring/
      - __init__.py       : 監視・ロギング・メトリクスの配置場所

ファイルの現在の最小構成（抜粋）:
```
src/kabusys/__init__.py         # "KabuSys - 日本株自動売買システム"
src/kabusys/data/__init__.py
src/kabusys/strategy/__init__.py
src/kabusys/execution/__init__.py
src/kabusys/monitoring/__init__.py
```

---

## 開発ガイドライン（簡易）

- 新しいモジュールやクラスを作る場合は、それぞれのサブパッケージ（data, strategy, execution, monitoring）に追加してください。
- 単体テストは pytest 等を用いて `tests/` フォルダに配置して実行してください。
- APIキーや機密情報は環境変数やシークレットマネージャーで管理し、コードやリポジトリに直書きしないでください。
- 実際の注文発行はテスト環境やペーパートレードで十分に検証した上で有効化してください。

例: ローカルテスト実行
```
pytest tests/
```

---

## 貢献・ライセンス

- 貢献歓迎します。プルリクエストや Issue を通じて機能追加やバグ修正を送ってください。
- ライセンスはプロジェクトに合わせて追加してください（例: MIT, Apache-2.0）。現状 README にライセンスは含まれていません。

---

不明点や追加してほしい機能（例: サンプル実装、外部API連携テンプレート、CI 設定など）があれば教えてください。README を拡張して具体的な実装例やワークフローを追記できます。