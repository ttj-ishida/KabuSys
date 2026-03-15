# KabuSys

日本株自動売買システム（KabuSys）の軽量な骨組みです。  
このリポジトリはパッケージ構成のみを提供しており、各サブパッケージ（データ取得、戦略、注文実行、監視）に具体的な実装を追加していくことを想定しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するためのモジュール構成を提供します。  
以下のサブパッケージを通じて、データ取得 → 売買戦略 → 注文実行 → 監視・ログ といったワークフローを実装できます。

- data: 市場データの取得や前処理
- strategy: 売買ロジック（シグナル生成）
- execution: 注文の発行・約定処理
- monitoring: ログ、メトリクス、アラート

現在のリポジトリはパッケージのスケルトンのみを含み、各モジュールの中身は実装を追加する必要があります。

---

## 機能一覧

このコードベースで提供する基本的な機能（設計上想定しているもの）

- パッケージ分割（モジュール化）により責務を明確化
  - data: 履歴データ、リアルタイムデータの取得インターフェース
  - strategy: シグナル生成、テスト用バックテストフレームワークのフック
  - execution: 証券会社API（例: kabuステーション等）への注文ラッパー
  - monitoring: 取引ログの記録、例外通知、メトリクス出力
- 簡易な初期化・バージョン管理（パッケージバージョンは __version__ に定義）
- 拡張しやすい構造（ユーザーが各サブパッケージに実装を追加）

※ 実際の売買ロジック、API認証、実注文処理等は本スケルトンには含まれていません。安全対策（例: サンドボックス環境、注文制限、リスク管理）は利用者が実装してください。

---

## セットアップ手順

このパッケージは Python プロジェクトとして使用します。以下は推奨のセットアップ手順です。

必要条件
- Python 3.8 以上（プロジェクトの実装方針に応じて適宜変更）
- git, pip

手順

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo-directory>
   ```

2. 仮想環境の作成（推奨）
   - venv を使う例:
     ```
     python -m venv .venv
     source .venv/bin/activate    # macOS / Linux
     .venv\Scripts\activate       # Windows
     ```

3. 開発インストール（`setup.py` または `pyproject.toml` がある場合）
   - プロジェクトにビルド設定がある場合:
     ```
     pip install -e .
     ```
   - もしビルド設定がない場合は、簡易的にルートを PYTHONPATH に含めるか、開発編集用に sys.path を使ってインポートしてください。

4. 依存パッケージのインストール
   - 必要な依存は実装によって変わります。まずは最低限 pytest や linter などを入れるとよいでしょう:
     ```
     pip install pytest flake8
     ```

---

## 使い方（基本例）

パッケージの基本的な使い方例を示します。現状はモジュールのみなので、まずはパッケージのバージョンやサブモジュールにアクセスする例です。

Python REPL またはスクリプトで:

```python
import kabusys

# バージョン確認
print(kabusys.__version__)  # 0.1.0

# サブパッケージ参照（各サブパッケージに実装を追加して利用）
import kabusys.data as data
import kabusys.strategy as strategy
import kabusys.execution as execution
import kabusys.monitoring as monitoring

# 例: 各サブパッケージに initialize() 関数等を実装している場合
# data.initialize(...)
# strategy.load_strategy(...)
# execution.connect(...)
# monitoring.start(...)
```

各サブパッケージに実際の機能（クラス・関数）を追加して、以下のようなワークフローを実装します。
1. data で過去データや価格ストリームを取得
2. strategy で売買シグナルを生成
3. execution で注文を発行／状態を管理
4. monitoring でログやアラートを記録

実装のヒント
- data: 抽象クラス（インターフェース）を定義し、実データソース（ファイル、API、WebSocket）ごとに具象クラスを作成する
- strategy: 入力は統一されたデータフォーマット（DataFrame など）にし、テスト容易性を高める
- execution: 注文の前に確認（サンドボックスモード）やリスク管理を挟む
- monitoring: ローカルログ、外部監視（Slack, Email）を切り替えられるようにする

---

## ディレクトリ構成

このリポジトリの現状の主要ファイル構成:

```
<project-root>/
└─ src/
   └─ kabusys/
      ├─ __init__.py         # パッケージ本体（__version__ など）
      ├─ data/
      │  └─ __init__.py      # データ取得関連モジュールを配置
      ├─ strategy/
      │  └─ __init__.py      # 売買戦略関連モジュールを配置
      ├─ execution/
      │  └─ __init__.py      # 注文実行関連モジュールを配置
      └─ monitoring/
         └─ __init__.py      # 監視・ログ関連モジュールを配置
```

現状では各サブパッケージの __init__.py は空のスケルトンです。必要に応じて以下のようにファイルを追加してください。

- src/kabusys/data/fetcher.py
- src/kabusys/strategy/basic.py
- src/kabusys/execution/api_client.py
- src/kabusys/monitoring/logger.py

---

## 拡張・実装ガイド（簡潔）

- テストを先に書く（TDD を推奨）
- 外部 API キー等の秘密情報は環境変数または別の設定ファイルで管理する
- 実運用前に必ずサンドボックス/ペーパートレードで動作検証する
- 注文処理には冪等性や再試行ロジック、エラーハンドリングを実装する

---

## 貢献

バグ報告や機能提案は Issue を作成してください。プルリクエストは歓迎します。  
実装の際はコードスタイル、テスト、ドキュメントを整備してください。

---

以上。必要であれば README に実際の使用例（サンプルスクリプト）や、pyproject.toml / setup.py のテンプレート、CI 設定なども追加できます。どの情報がさらに欲しいか教えてください。