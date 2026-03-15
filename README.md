# KabuSys

KabuSys は日本株向けの自動売買システムのベースとなるPythonパッケージです。モジュール構成を分離しており、データ取得（data）、売買戦略（strategy）、注文実行（execution）、監視（monitoring）をそれぞれ実装・拡張できるように設計されています。

バージョン: 0.1.0

---

## 概要

このリポジトリは自動売買システムの骨組み（スケルトン）を提供します。各機能は独立したモジュールに分けられており、以下を目的としています。

- データ取得ロジック（板情報・約定・日足など）の実装
- 売買戦略の実装（シグナル生成）
- 実際の注文送信を行う実行（ブローカーAPI接続）
- ログやモニタリング・アラート機能

現状はパッケージ構成のみを提供しており、具体的なデータソースやAPIクライアントは利用者が実装して拡張することを想定しています。

---

## 主な機能（想定）

- データプロバイダを差し替え可能な設計
- 戦略ごとに分離された実装（テストしやすい）
- 注文実行インターフェース（APIクライアントを実装して接続）
- 監視・ログ出力による稼働状態の把握

※ 現状はベースパッケージのみを提供します。上記機能は各モジュールを実装することで利用可能になります。

---

## 要件

- Python 3.8 以上推奨
- 追加の依存パッケージは現状特にありません（APIクライアントやデータ処理ライブラリを導入する場合は別途 requirements を追加してください）。

---

## セットアップ手順

開発環境の例（仮想環境を使用）:

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境作成と有効化（例: venv）
   ```
   python -m venv .venv
   # Unix / macOS
   source .venv/bin/activate
   # Windows (PowerShell)
   .\.venv\Scripts\Activate.ps1
   ```

3. ローカル開発インストール
   プロジェクトルートに `pyproject.toml` や `setup.py` がある場合は以下のようにインストールします（現状パッケージのみのため、各自でパッケージ化してください）。
   ```
   pip install -e .
   ```
   ※ 上記が使えない場合: `PYTHONPATH` に `src` を追加して実行する方法もあります。
   ```
   export PYTHONPATH=$(pwd)/src:$PYTHONPATH
   ```

---

## 使い方（基本）

パッケージをインポートしてバージョンやモジュールを参照できます。現行のモジュール構成は以下の通りです。

サンプル:
```python
import kabusys

print("KabuSys version:", kabusys.__version__)

# モジュール群（実装を追加して利用）
import kabusys.data
import kabusys.strategy
import kabusys.execution
import kabusys.monitoring
```

各モジュールには実際の実装を追加する必要があります。実装例（骨組み）の雛形：

- src/kabusys/data/provider.py
```python
class BaseDataProvider:
    def get_price(self, symbol):
        raise NotImplementedError
```

- src/kabusys/strategy/my_strategy.py
```python
class MyStrategy:
    def generate_signal(self, market_data):
        # True = buy, False = sell/hold 等
        return None
```

- src/kabusys/execution/client.py
```python
class ExecutionClient:
    def send_order(self, symbol, side, quantity):
        # ブローカーAPIへ注文を送る実装
        pass
```

- src/kabusys/monitoring/logger.py
```python
def log_event(message):
    # ログ保存・外部通知の実装
    print(message)
```

これらを組み合わせて、データ取得 -> シグナル生成 -> 注文実行 -> 監視 の流れを作ります。

---

## 開発・拡張ガイド（簡易）

1. data モジュールにデータソース（APIクライアントやCSV読み込み等）を実装する。
2. strategy モジュールに戦略クラスを作り、単体テストを書いてロジックを検証する。
3. execution モジュールにブローカーへの接続クライアントを実装する（認証や注文管理）。
4. monitoring モジュールにログや通知（Slack, メール等）を実装する。
5. 各パーツはインターフェース（抽象クラス）を定義して差し替え可能にしておくと良い。

テストやCIの導入、設定ファイル（APIキー等）の安全な管理（環境変数やVaultの利用）も推奨します。

---

## ディレクトリ構成

現状の主要ファイルは以下の通りです。

- src/
  - kabusys/
    - __init__.py               # パッケージ初期化 (version, __all__)
    - data/
      - __init__.py             # データ取得関連モジュール群用パッケージ（実装追加）
    - strategy/
      - __init__.py             # 戦略モジュール群用パッケージ（実装追加）
    - execution/
      - __init__.py             # 注文実行モジュール群用パッケージ（実装追加）
    - monitoring/
      - __init__.py             # 監視・ログモジュール群用パッケージ（実装追加）

ファイルの内容（抜粋）:
- src/kabusys/__init__.py
  - ドキュメント文字列と __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]

---

## 注意事項

- 本リポジトリは「骨組み（テンプレート）」です。実際に日本株の注文を行うには、ブローカーAPI（例: Kabuステーション等）への接続実装と十分なテストが必要です。
- 実取引前には必ずシミュレーション環境での検証・リスク管理を行ってください。

---

必要であれば、README に含める具体的な実装例（データ取得クラス、注文クライアントのサンプル、テスト例など）を追加で作成します。どの部分を優先して実装したいか教えてください。