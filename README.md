# KabuSys

KabuSys は日本株の自動売買システム用の軽量なフレームワーク骨組みです。データ取得、売買戦略、注文実行、監視の4つの責務を分離したモジュール構成を提供します。プロトタイプ／POC（概念実証）や、独自アルゴリズムの実装・検証の出発点として利用できます。

バージョン: 0.1.0

---

## 機能一覧

- data: 市場データ取得・前処理のためのプレースホルダモジュール
- strategy: 売買ロジック（シグナル生成）の実装場所
- execution: 注文送信や約定管理を行うモジュール
- monitoring: ログ記録、パフォーマンス監視、アラートなどの監視用モジュール

現状はフレームワークの骨組みのみ（各モジュールはパッケージとして存在）です。各モジュールに具体的な実装を追加して利用します。

---

## セットアップ手順

前提
- Python 3.8 以上を想定（プロジェクト要件に応じて調整してください）

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ名>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージのインストール
   - まだ `pyproject.toml` / `setup.py` / `requirements.txt` がない場合は、開発時はソースをパスに追加して利用できます（下記参照）。
   - パッケージ形式が用意されている場合:
     ```
     pip install -e .
     ```
   - パッケージ化されていない場合（開発中）:
     ```
     # プロジェクトルートから
     export PYTHONPATH=$PWD/src:$PYTHONPATH   # macOS / Linux
     set PYTHONPATH=%cd%\src;%PYTHONPATH%     # Windows (PowerShell / cmd での書き方に注意)
     ```

4. （任意）依存ライブラリを requirements.txt にまとめた場合:
   ```
   pip install -r requirements.txt
   ```

---

## 使い方

パッケージの基本的な使い方例です。各モジュールの具体的な API はプロジェクトで実装してください。ここでは基本的なインポート例と、拡張ポイントの例を示します。

- パッケージをインポートしてバージョンを確認する
```python
import kabusys
print(kabusys.__version__)   # 例: "0.1.0"
```

- サブパッケージへアクセスする
```python
import kabusys.data as data
import kabusys.strategy as strategy
import kabusys.execution as execution
import kabusys.monitoring as monitoring
```

- 戦略の簡単な雛形（例）
```python
# my_strategy.py
class MyStrategy:
    def __init__(self, data_source, executor, monitor):
        self.data_source = data_source
        self.executor = executor
        self.monitor = monitor

    def run_once(self):
        # 1) データ取得
        df = self.data_source.fetch_latest()

        # 2) シグナル生成（ユーザー実装）
        signals = self.generate_signals(df)

        # 3) 注文実行
        for sig in signals:
            self.executor.send_order(sig)

        # 4) 監視／ログ
        self.monitor.record(signals)

    def generate_signals(self, df):
        # ユーザーが実装するロジック
        return []
```

上記はあくまでサンプルの雛形です。実際には API の仕様（メソッド名や引数、戻り値）をプロジェクト内で決めて実装してください。

---

## ディレクトリ構成

現在のファイル構成（主要ファイル）:
```
<project-root>/
├─ src/
│  └─ kabusys/
│     ├─ __init__.py          # パッケージ定義 (バージョンなど)
│     ├─ data/
│     │  └─ __init__.py       # データ取得モジュール（プレースホルダ）
│     ├─ strategy/
│     │  └─ __init__.py       # 戦略実装モジュール（プレースホルダ）
│     ├─ execution/
│     │  └─ __init__.py       # 注文実行モジュール（プレースホルダ）
│     └─ monitoring/
│        └─ __init__.py       # 監視・ログモジュール（プレースホルダ）
└─ README.md
```

- src/kabusys/__init__.py
  - プロジェクトのバージョンや公開モジュール（__all__）を定義しています。
- 各サブパッケージ（data, strategy, execution, monitoring）は現状空の package プレースホルダです。ここに実装を追加していきます。

---

補足
- 本リポジトリはフレームワークの骨組みを提供することを目的としています。実運用には API の厳密な定義、例外処理、ログ、テスト、セキュリティ（認証・秘匿情報の管理）などの実装が必要です。
- テストや CI、ドキュメントの追加を推奨します。

必要であれば、各モジュールの詳細なインターフェース設計（例えば DataSource の必須メソッド、Executor の注文フォーマット、Monitoring の記録フォーマット）やテンプレート実装の雛形を作成します。どのレベルまで詳細が欲しいか教えてください。