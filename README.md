# KabuSys

日本株自動売買システム（KabuSys）の骨組みパッケージです。  
このリポジトリは、データ収集、戦略（ストラテジー）、注文実行、モニタリングの4つの主要コンポーネントを想定したモジュール構成を提供します。現状はパッケージの基本構造のみを含み、各モジュールの実装は今後追加していく想定です。

バージョン: 0.1.0

---

## 概要

KabuSysは日本株の自動売買システムを構築するためのフレームワーク（骨組み）です。  
各責務を分離したモジュール設計（data, strategy, execution, monitoring）により、実装の差し替えやテストしやすい構成を目指しています。

主な目的:
- 市場データの取得・前処理（data）
- 売買シグナルの生成（strategy）
- 注文の発行・約定管理（execution）
- 実行状況・ログ・アラートの監視（monitoring）

---

## 機能一覧（想定 / これから実装する機能）

- data
  - 銘柄情報・板情報・約定履歴の取得インターフェース
  - 履歴データのキャッシュ／前処理
- strategy
  - 売買ルール（シグナル）生成の抽象クラス・テンプレート
  - バックテスト用の簡易実行フロー
- execution
  - 注文送信インターフェース（成行・指値）
  - 注文状態管理（未約定・部分約定・約定）
  - APIコネクタ（※証券会社APIのラッパー実装を想定）
- monitoring
  - ログ収集・出力（ファイル／外部サービス）
  - アラート（メールやSlackなど）の通知インターフェース
  - ライブ監視・ダッシュボードの土台

※現在のリポジトリは上記モジュールの「パッケージ構成」を提供しており、具体的な実装は含まれていません。実装は各モジュール内に追加してください。

---

## セットアップ手順

前提:
- Python 3.8 以上を推奨

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境を作成して有効化
   - macOS / Linux:
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     py -3 -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存関係のインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - 現状依存パッケージがなければ不要です。

4. 開発インストール（パッケージング設定がある場合）
   - pyproject.toml / setup.cfg 等が整っている場合:
     ```
     pip install -e .
     ```
   - ない場合は、プロジェクト直下の `src` を PYTHONPATH に含めるか、上記の開発インストール設定を追加してください。

---

## 使い方（例）

パッケージのバージョン確認:
```python
import kabusys
print(kabusys.__version__)  # -> "0.1.0"
```

基本的なインポート例:
```python
# モジュールの雛形としてインポート
from kabusys import data, strategy, execution, monitoring
```

各モジュールに対する実装例（テンプレート）:
- strategy のサンプルクラス
```python
# 例: src/kabusys/strategy/simple_strategy.py に実装するイメージ
class SimpleStrategy:
    def __init__(self, params):
        self.params = params

    def generate_signal(self, market_data):
        # market_data をもとに売買シグナルを返す (例: 'buy', 'sell', None)
        return None
```

- execution のサンプルクラス
```python
# 例: src/kabusys/execution/execution_engine.py に実装するイメージ
class ExecutionEngine:
    def __init__(self, api_client):
        self.api = api_client

    def send_order(self, symbol, side, quantity, price=None):
        # 証券APIへ注文を飛ばす処理
        pass

    def get_order_status(self, order_id):
        pass
```

- monitoring のサンプル
```python
# 例: src/kabusys/monitoring/logger.py
class Monitoring:
    def log(self, message):
        print(message)

    def alert(self, message):
        # メールやSlackへの通知を実装
        pass
```

実際のワークフロー例（擬似コード）:
```python
# 1) データ取得
md = data.Provider().get_latest('7203')  # トヨタの例

# 2) シグナル生成
sig = strategy.SimpleStrategy(params).generate_signal(md)

# 3) 注文実行
if sig == 'buy':
    order = execution.ExecutionEngine(api).send_order('7203', 'buy', 100)

# 4) モニタリング
monitoring.Monitoring().log(f"Order sent: {order}")
```

---

## ディレクトリ構成

現状のファイル構成（最小構成）:

- src/
  - kabusys/
    - __init__.py
    - data/
      - __init__.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

READMEやテスト、パッケージ設定ファイルはプロジェクトルートに配置することを推奨します（例: README.md, pyproject.toml, setup.cfg, requirements.txt, tests/）。

---

## 開発ガイドライン（簡易）

- 各サブパッケージ（data/ strategy/ execution/ monitoring/）は単一責任を保つこと。
- 可能な限りインターフェース（抽象クラス）を用意して差し替え可能にする。
- サードパーティAPIを直接叩く部分はラッパー化してモック可能にする（テスト容易性向上）。
- ロギングは標準の logging モジュールを利用し、モニタリングモジュール経由で出力できるようにする。

---

## 今後の拡張案

- 各モジュールの具体実装（証券会社API接続、戦略ライブラリ、バックテストエンジンなど）
- CI（自動テスト、リンティング）
- ドキュメントの充実（APIリファレンス、設計ドキュメント）
- 実運用向けの安全装置（損切り、取引制限、フェイルセーフ）

---

必要であれば、このREADMEをベースに「初期実装のテンプレート」「サンプル戦略」「バックテストの簡易フレームワーク」などの追加ドキュメントも作成します。どの部分から着手したいか教えてください。