# KabuSys

KabuSys は日本株向けの自動売買システムの基礎となるPythonパッケージのテンプレートです。本リポジトリは、データ取得、売買戦略、注文実行、監視の責務を分離したモジュール構成を提供します。実際の取引APIや戦略は含まれていないため、拡張・実装して利用します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の4つの主要コンポーネントで構成される自動売買フレームワークの骨組みです。

- data: 市場データや銘柄情報の取得・前処理
- strategy: 売買ロジック（シグナル生成）
- execution: 注文送信・約定管理
- monitoring: ログ、メトリクス、状態監視

※このリポジトリは「骨組み（スケルトン）」であり、取引所APIや具体的な戦略は含まれていません。ユーザーが各モジュールを実装して運用します。

---

## 機能一覧

現状（初期テンプレート）で提供するもの:

- Pythonパッケージ構成（src レイアウト）
- モジュール分割（data / strategy / execution / monitoring）
- パッケージのメタデータ（バージョン情報等）

拡張して実装する想定の機能（例）:

- リアルタイム・過去データの取得コネクタ（kabuステーション / 証券API 等）
- テクニカル指標の計算モジュール
- 注文送信・約定管理（成行・指値・IFD/OCO等）
- ログ、アラート、ダッシュボード連携

---

## 動作環境（推奨）

- Python 3.8 以上
- pip（パッケージ管理）
- （任意）仮想環境（venv / virtualenv / conda）

---

## セットアップ手順

1. リポジトリをクローンする（例）:
   ```
   git clone <repository-url>
   cd <project-root>
   ```

2. 仮想環境の作成（推奨）:
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストールする  
   リポジトリに `pyproject.toml` / `requirements.txt` / `setup.py` がある場合はそれに従ってください。一般的な方法:
   ```
   pip install -r requirements.txt
   ```
   または開発中は編集可能インストール:
   ```
   pip install -e .
   ```
   （上記はプロジェクトにパッケージ設定ファイルが存在することが前提です）

4. 設定ファイル / 環境変数の準備  
   実際の取引APIを使う場合はAPIキーやエンドポイントを環境変数や設定ファイルで管理してください（例）:
   - KABU_API_TOKEN
   - KABU_API_ENDPOINT
   これらはサンプルであり、利用するブローカーAPIに合わせてください。

---

## 使い方（基本）

このパッケージはモジュール分割のみ行われています。まずはパッケージがインポートできることを確認します。

Python REPL やスクリプトで:
```python
import kabusys
print(kabusys.__version__)  # 0.1.0
```

各コンポーネントの実装例（テンプレート）を以下に示します。これらはあくまで一例です。

- data/provider.py（例）
```python
# data/provider.py
class DataProvider:
    def get_price(self, symbol, timeframe):
        """価格データを取得して返す（DataFrame等）"""
        raise NotImplementedError
```

- strategy/base.py（例）
```python
# strategy/base.py
class Strategy:
    def on_price(self, price):
        """価格更新を受け取って売買シグナルを返す"""
        raise NotImplementedError
```

- execution/adapter.py（例）
```python
# execution/adapter.py
class ExecutionAdapter:
    def send_order(self, order):
        """注文を送信する"""
        raise NotImplementedError
```

- monitoring/logger.py（例）
```python
# monitoring/logger.py
def log_event(event):
    """イベントをログ出力する（ファイル、標準出力、外部サービス等）"""
    print(event)
```

簡単なフロー（概念）:
1. DataProvider が価格を取得／ストリーミング
2. Strategy が価格イベントを受けてシグナル生成（買い/売り/何もしない）
3. ExecutionAdapter がシグナルに応じて注文を発行
4. Monitoring が状態・ログ・アラートを記録

---

## ディレクトリ構成

リポジトリの現在の構成（主要ファイルのみ）:

- src/
  - kabusys/
    - __init__.py           # パッケージ定義（バージョン等）
    - data/
      - __init__.py         # data モジュール（データ取得・加工）
    - strategy/
      - __init__.py         # strategy モジュール（売買ロジック）
    - execution/
      - __init__.py         # execution モジュール（注文実行）
    - monitoring/
      - __init__.py         # monitoring モジュール（ログ・監視）

READMEや設定ファイル、テスト等はプロジェクトルートに配置してください（例: README.md、requirements.txt、config.yaml）。

---

## 開発ガイド（拡張方法）

- 新しいデータソースを追加する場合:
  - data/ 以下にプロバイダクラスを作成し、共通インタフェース（例: get_price）を実装する
- 新しい戦略を追加する場合:
  - strategy/ 以下に戦略クラスを実装し、on_price などのハンドラを定義する
- 注文実行の実装:
  - execution/ にブローカーごとのアダプタを作成。テスト環境用に「モック」アダプタを用意することを推奨
- 監視・ログ:
  - monitoring/ でログ出力やメトリクス（Prometheus 等）、アラート（Slack 等）連携を実装

テストやCIの導入も推奨します。実運用前にペーパートレードやシミュレーションで十分に検証してください。

---

## 注意事項

- 実際の資金を使った自動売買では法規制、ブローカーの利用規約、リスク管理に十分注意してください。
- 本テンプレート自体は取引機能を持ちません。実運用する場合は、APIキーの安全管理、例外処理、接続再試行、ログ保持、フェイルセーフ等を必ず実装してください。

---

## 貢献・問い合わせ

- バグ報告や機能提案はIssueを立ててください。
- プルリクエスト歓迎。コーディング規約やテストを含めていただけると助かります。

---

作成者: 本テンプレートは自動売買システムの雛形として設計されています。実装の際は必ず十分な検証と安全対策を行ってください。