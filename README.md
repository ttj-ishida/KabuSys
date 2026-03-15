# KabuSys

日本株自動売買システムのための軽量な骨組み（スケルトン）パッケージです。  
現時点ではパッケージの基本構造（モジュール分割とバージョン情報）のみ実装されています。実際のデータ取得・売買実行・ストラテジ・監視機能は、プロジェクトに合わせて実装していく想定です。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株の自動売買システム構築のためのフレームワーク的なパッケージです。以下の責務ごとにモジュールを分離しています。

- data: 市場データの取得・前処理
- strategy: 取引戦略の実装
- execution: 注文の送信・約定処理（ブローカー API とのインターフェース）
- monitoring: ログ・メトリクス・アラート等の監視機能

現状はパッケージの骨組みのみで、各モジュールは空のパッケージとして定義されています。実装を追加して利用してください。

---

## 機能一覧（想定・現状）

現状:
- パッケージの基本構成（kabusys パッケージとサブパッケージ）
- バージョン情報（__version__ = "0.1.0"）

想定（今後実装する機能の例）:
- 株価データの取得（過去データ・リアルタイムティック）
- 指標・テクニカル指標の計算（移動平均、RSI 等）
- 売買ストラテジの定義とバックテスト
- ブローカー（例: kabuステーション 等）への注文送信モジュール
- ログ、メトリクス、アラートの統合的監視

---

## セットアップ手順

このリポジトリは Python パッケージとして構成されています。以下はローカル開発環境での基本的なセットアップ手順です。

前提:
- Python 3.8 以上（プロジェクトに合わせて適宜変更してください）
- git が利用可能

手順:

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. パッケージを開発モードでインストール
   ```
   pip install --upgrade pip
   pip install -e .
   ```

4. （任意）依存ライブラリを追加する場合
   - このスケルトンには依存関係ファイルが含まれていません。Pandas、NumPy、requests、websocket-client 等が必要になる可能性があります。
   ```
   pip install pandas numpy requests
   ```

---

## 使い方（基本）

現状では振る舞いを持つコードは含まれていませんが、パッケージのインポートとバージョン確認は可能です。

Python REPL やスクリプトで:
```python
import kabusys

print(kabusys.__version__)   # "0.1.0"
print(kabusys.__all__)       # ['data', 'strategy', 'execution', 'monitoring']
```

各サブパッケージはモジュールのプレースホルダとして存在します。実装例（ストラテジを追加する場合）:

- src/kabusys/strategy/my_strategy.py を作成して Strategy クラスを実装
- src/kabusys/data/ 以下にデータ取得モジュールを追加
- src/kabusys/execution/ 以下に注文送信ラッパーを実装
- src/kabusys/monitoring/ 以下にログやメトリクス出力を実装

簡単なテンプレート例:
```python
# src/kabusys/strategy/example.py
class Strategy:
    def __init__(self, config):
        self.config = config

    def on_market_data(self, data):
        # データを受け取り売買判断を行う
        pass

    def on_order_update(self, order):
        # 注文状態の更新を受け取る
        pass
```

---

## ディレクトリ構成

現状のファイル構成は以下のとおりです（抜粋）:

- src/
  - kabusys/
    - __init__.py            # パッケージ定義、__version__, __all__
    - data/
      - __init__.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

具体的ファイル:
- src/kabusys/__init__.py
  - """KabuSys - 日本株自動売買システム"""
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]
- src/kabusys/data/__init__.py
- src/kabusys/strategy/__init__.py
- src/kabusys/execution/__init__.py
- src/kabusys/monitoring/__init__.py

---

## 開発・拡張のヒント

- まずは data モジュールにデータフェッチ用のインターフェース（抽象クラス）を定義し、CSV / API / Websocket など複数実装を用意すると拡張しやすいです。
- strategy モジュールはライフサイクル（初期化、データ受信、注文確認）のコールバックメソッドを定義するインターフェースを提供すると良いです。
- execution モジュールはブローカーごとのアダプタパターンで実装し、共通の注文 API を公開すると切り替えが容易です。
- monitoring はログ（構造化ログ）、メトリクス（Prometheus 等）、障害通知（Slack / Email）の統合を検討してください。
- 危険回避のため、実取引前に十分なバックテスト・シミュレーション・安全弁（最大注文量、取引停止フラグ等）を組み込みましょう。

---

必要があれば、README に以下を追加できます:
- 具体的な依存パッケージ一覧（requirements.txt）
- テスト方法（pytest 等）
- CI/CD 設定例
- サンプル戦略とバックテスト例

ご希望があれば、上記のうちどれを優先して追加するか教えてください。