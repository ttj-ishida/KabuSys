# KabuSys

KabuSys は日本株の自動売買システムの基盤となる Python パッケージです。  
このリポジトリはプロジェクトの最小構成（パッケージ定義）を提供しており、データ取得、売買戦略、注文実行、監視の各責務を分離して実装できるようになっています。

バージョン: 0.1.0

---

## 概要

このプロジェクトは、以下の4つの主要コンポーネントに分かれたモジュール構成を提供します。

- data: 市場データの取得・加工
- strategy: 売買ロジック（シグナル生成）
- execution: 注文の発行・発注管理
- monitoring: 稼働状況の監視・ログ・メトリクス収集

現状はパッケージのスケルトンのみを含み、実際の API 呼び出しや戦略ロジックはユーザーが実装することを前提としています。

---

## 主な機能（予定・想定）

- 市場データの取得・キャッシュ機能（data）
- 複数の売買戦略をプラグイン的に追加・切替（strategy）
- 注文発注、発注結果の追跡・再送（execution）
- 稼働監視、ログ集約、アラート送信（monitoring）
- バックテスト／フォワードテストのためのフレームワーク（将来的な拡張）

（注）現時点では上記は設計方針・想定機能です。具体的な実装は各モジュールに追加してください。

---

## セットアップ手順

前提: Python 3.8 以上を推奨します。

1. リポジトリをクローンする
   ```
   git clone <リポジトリ URL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成して有効化（推奨）
   - Unix/macOS:
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール  
   このリポジトリは依存関係の定義ファイル（requirements.txt / pyproject.toml / setup.py）が含まれていないため、必要なパッケージをプロジェクトに応じてインストールしてください。例:
   ```
   pip install requests pandas numpy
   ```

4. 開発中にローカルの src 配下のパッケージを使う方法
   - 方法 A: PYTHONPATH を設定
     ```
     export PYTHONPATH=$(pwd)/src:$PYTHONPATH    # Unix/macOS
     set PYTHONPATH=%cd%\src;%PYTHONPATH         # Windows
     ```
   - 方法 B: editable インストール（プロジェクトに setup.py / pyproject.toml がある場合）
     ```
     pip install -e .
     ```

---

## 使い方

このパッケージはフレームワークの骨組みを提供します。以下は基本的な利用例（概念的なコード）です。実際のメソッドやクラスはプロジェクトで追加してください。

- 基本インポート
  ```python
  import kabusys

  print(kabusys.__version__)  # "0.1.0"
  from kabusys import data, strategy, execution, monitoring
  ```

- 各モジュールの責務（実装ガイド）
  - data:
    - 市場データフェッチャ（例: REST/WebSocket 経由で株価を取得）
    - データ前処理、インジケータ計算
  - strategy:
    - StrategyBase クラスを定義して、シグナル（買い/売り/保持）を返す
    - パラメータ管理、バックテスト用の切替
  - execution:
    - 注文送信・キャンセル・注文状況の追跡
    - 約定確認・証券会社 API との接続ラッパー
  - monitoring:
    - ロギング、アラート（メール/SNS 等）の送信
    - メトリクスの収集（例: Prometheus へエクスポート）

- 典型的な制御フロー（擬似コード）
  ```python
  # 1) データ取得
  df = data.fetch_ohlcv("7203.T", period="1m")

  # 2) 戦略でシグナル生成
  sig = strategy.MyStrategy().generate_signal(df)

  # 3) シグナルに基づき注文を実行
  execution.ExecutionManager().execute(sig, symbol="7203.T")

  # 4) 実行状況を監視
  monitoring.Monitor().report()
  ```

---

## ディレクトリ構成

リポジトリにある主要ファイル・ディレクトリは以下の通りです。

- src/
  - kabusys/
    - __init__.py          # パッケージのメタ情報（__version__ 等）
    - data/
      - __init__.py        # data モジュール（データ取得処理を実装）
    - strategy/
      - __init__.py        # strategy モジュール（売買ロジックを実装）
    - execution/
      - __init__.py        # execution モジュール（注文実行処理）
    - monitoring/
      - __init__.py        # monitoring モジュール（監視・ログ）

現状は各サブパッケージが空の初期化ファイルのみを含みます。各領域に必要なモジュールやクラスを追加していってください。

---

## 開発ガイドライン（簡易）

- 新しい機能は対応するサブパッケージ（data/ strategy/ execution/ monitoring/）の下に追加してください。
- 単体テストを作成する場合は tests/ ディレクトリを作成し pytest などを用いてください。
- 外部 API（証券会社の API）を使う際は API キー等の機密情報を環境変数または安全なシークレット管理で扱ってください。

---

必要に応じて、具体的なクラス設計やサンプル実装（例: StrategyBase、ExecutionManager、DataFetcher のテンプレート）を作成できます。どのコンポーネントから実装したいか教えてください。