# KabuSys

KabuSys は日本株向けの自動売買システムの骨組み（スケルトン）です。データ取得、売買ストラテジー、発注（Execution）、運用監視（Monitoring）をモジュール化して提供することを想定したパッケージの初期構成です。

バージョン: 0.1.0

---

## 主な目的（プロジェクト概要）
- 日本株の自動売買システム構築のための基盤パッケージ
- 各責務（データ提供 / ストラテジー / 発注 / 監視）を分離し、拡張しやすい設計を想定
- 実際の証券会社APIやバックテスト基盤と結合して利用するための出発点を提供

---

## 機能一覧（予定・想定）
- data: 市場データ取得やヒストリカルデータの読み込み用モジュールの配置場所
- strategy: 売買ロジック（ストラテジー）を実装する場所
- execution: 注文発行や約定管理を行うエンジン（証券会社APIとの結合点）
- monitoring: 稼働状況の監視／ログ／アラートなどを実装する場所
- パッケージ情報（バージョン管理など）

※現状はパッケージ構造のみで、具体的な実装は含まれていません。各モジュールを実装して拡張してください。

---

## 前提条件
- Python 3.8 以上を推奨
- 仮想環境（venv, pyenv, conda など）での運用を推奨
- 実際に取引する場合は、利用する証券会社のAPIキーや接続情報が別途必要

---

## セットアップ手順

1. リポジトリをクローン
   - 例: `git clone <リポジトリURL>`

2. 仮想環境の作成（任意だが推奨）
   - Python の venv を利用する例:
     - `python -m venv .venv`
     - macOS / Linux: `source .venv/bin/activate`
     - Windows: `.venv\Scripts\activate`

3. 依存パッケージのインストール
   - 本リポジトリに requirements.txt / pyproject.toml / setup.py があればそれに従ってください。
   - まだ無ければ、必要なライブラリ（例: requests, pandas, websocket-client など）を個別にインストールしてください。
     - 例: `pip install requests pandas`

4. ソースから使う方法（2通り）
   - (A) 開発モードでインストール（プロジェクトに setup.py / pyproject.toml がある場合）
     - `pip install -e .`
   - (B) 一時的にパッケージをパスに追加して利用
     - 実行時に `PYTHONPATH=src` を通す、またはスクリプト側で `sys.path.append("src")` を追加

---

## 使い方（基本例）

このパッケージは各機能ごとにサブパッケージを提供します。現状は空パッケージですが、下記のように利用を想定しています。

- 基本的なインポートとバージョン確認
```python
import kabusys
print(kabusys.__version__)  # "0.1.0"
```

- サブモジュール群
```python
import kabusys.data       # データ提供モジュール
import kabusys.strategy   # ストラテジー実装用
import kabusys.execution  # 注文発行エンジン
import kabusys.monitoring # 監視・ログ用
```

- ストラテジー / 実行の設計例（推奨インターフェイスのサンプル）
  - 実装状況に依存しますが、次のような抽象クラス／インターフェイスを作ると拡張しやすくなります。

```python
# strategy/base.py (例)
class BaseStrategy:
    def on_market_data(self, tick):
        """市場データを受け取り、売買シグナルを返す"""
        raise NotImplementedError

    def on_order_update(self, order):
        """注文状態の更新を処理する"""
        pass
```

```python
# execution/engine.py (例)
class ExecutionEngine:
    def place_order(self, symbol, side, qty, price=None):
        """注文を発行する"""
        raise NotImplementedError

    def cancel_order(self, order_id):
        """注文をキャンセルする"""
        raise NotImplementedError
```

- 簡単な運用フロー（概念）
  1. DataProvider がティックや板情報を受信
  2. Strategy にデータを渡し、売買判断（シグナル）を得る
  3. Execution が証券会社APIへ注文を発行
  4. Monitoring が稼働状況／エラーを監視・通知する

---

## ディレクトリ構成

以下は現状のプロジェクト構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py                 # パッケージのメタ情報（バージョンなど）
    - data/
      - __init__.py               # データ関連モジュール配置場所
    - strategy/
      - __init__.py               # ストラテジー実装場所
    - execution/
      - __init__.py               # 注文発行・実行エンジン場所
    - monitoring/
      - __init__.py               # 監視・ログ・アラートなど

ファイル例:
- src/kabusys/__init__.py
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]
- src/kabusys/data/__init__.py
- src/kabusys/strategy/__init__.py
- src/kabusys/execution/__init__.py
- src/kabusys/monitoring/__init__.py

---

## 拡張・実装のヒント
- 各サブパッケージに抽象基底クラス（ABC）を定義し、実装者はそれを継承する形にすると統一的な扱いができます。
- 実取引を行う場合は必ずサンドボックスやデモ口座で十分にテストを行ってください。資金リスクがあります。
- ロギングとエラーハンドリングは入念に実装してください。注文エラーや接続断に対するリトライ戦略が重要です。
- 単体テスト・統合テストを用意して、自動化（CI）で回すことを推奨します。

---

## 貢献
- バグ報告や機能提案は Issue を作成してください。
- Pull Request は歓迎します。実装する場合はテストを添えてください。

---

## ライセンス
- このリポジトリにライセンスファイルがない場合、利用・配布の前にライセンス方針を明確にしてください。

---

この README は現行コードベース（空のサブパッケージ構成）をもとにしたテンプレートです。各モジュールの具体的な API を実装したら、使い方やサンプルコードを README に追記してください。