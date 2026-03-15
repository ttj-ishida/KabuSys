# KabuSys

KabuSys は日本株の自動売買を目的とした軽量なパッケージの骨組みです。データ収集、売買戦略、約定実行、監視の各コンポーネントを分離して実装できるように設計されています。このリポジトリはプロジェクトの初期構成（パッケージ/モジュールの骨組み）を提供します。

バージョン: 0.1.0

---

## 機能一覧（想定/設計）
現在のコードベースはパッケージ構成のみですが、想定している主要機能は以下です。

- data: 市場データの取得・整形（板情報、歩み値、OHLCV 等）
- strategy: 売買ロジック・シグナル生成（バックテスト用のインターフェース含む）
- execution: 注文送信、約定管理、リスク制御
- monitoring: ログ収集、アラート、稼働状況の可視化（Web UIや通知連携）

各機能は独立したサブパッケージとして実装し、必要に応じて外部 API（証券会社 API）や DB、メッセージングを組み合わせます。

---

## 必要条件
- Python 3.8 以上（プロジェクトポリシーに合わせて変更してください）
- 仮想環境の利用を推奨
- 実際の取引を行う場合は、証券会社が提供する API アクセス情報（API key / secret）やテスト環境の準備が必要

依存ライブラリはまだ定義されていません。実装に合わせて `requirements.txt` または `pyproject.toml` に追加してください。一般的に使われるライブラリ例：
- requests / aiohttp
- pandas / numpy
- websocket-client / websockets
- pydantic / pyyaml（設定管理）
- loguru / structlog（ログ）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリ URL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成して有効化（例: venv）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   - まだ requirements.txt が用意されていない場合は、実装に応じて作成してください。
   - 開発中は編集を反映しやすいようにローカルインストール（編集可能）を推奨:
     ```
     pip install -e .
     ```
     （setup.py / pyproject.toml がある場合）

4. （任意）Lint / フォーマットのセットアップ
   ```
   pip install black flake8 isort
   ```

---

## 使い方（簡易例）

このパッケージはモジュールの骨組みのみ提供しています。まずは基本的な確認例を示します。

- バージョン確認:
  ```python
  import kabusys
  print(kabusys.__version__)  # -> "0.1.0"
  ```

- サブパッケージの参照例（各サブパッケージは実装次第で利用可能）
  ```python
  from kabusys import data, strategy, execution, monitoring

  # 各モジュール内に実装を追加して呼び出します
  # 例: data.fetch_ohlcv("7203.T")
  # 例: strategy.MyStrategy(config).generate_signals(df)
  # 例: execution.send_order(order)
  # 例: monitoring.start_dashboard()
  ```

- 設定ファイル（例: config.yaml）
  ```yaml
  api:
    kabucom:
      api_key: "<YOUR_API_KEY>"
      secret: "<YOUR_SECRET>"
      base_url: "https://api.kabu.example"
  trading:
    account: "1234567"
    default_qty: 100
  logging:
    level: INFO
  ```

- 実装のヒント
  - data パッケージ: データ取得は非同期（async）/同期どちらでも良いが、一貫性を保つ。
  - strategy: 「シグナル生成」と「ポジション管理」を分離するインターフェースを設計する。
  - execution: 注文送信時は冪等性・注文状態管理（未約定/一部約定/約定）を確実に実装する。
  - monitoring: 稼働監視、注文/約定ログ、アラート（Slack/メール）を設ける。

---

## ディレクトリ構成

このリポジトリの現状の最小構成は以下の通りです。

- src/
  - kabusys/
    - __init__.py            # パッケージ初期化、バージョン等
    - data/
      - __init__.py          # データ取得モジュール（実装場所）
    - strategy/
      - __init__.py          # 戦略実装モジュール（実装場所）
    - execution/
      - __init__.py          # 注文・約定処理モジュール（実装場所）
    - monitoring/
      - __init__.py          # 監視／ログ／アラート（実装場所）

（将来的にテスト、サンプル、ドキュメント等のディレクトリを追加することを推奨します）
例:
- tests/
- examples/
- docs/
- requirements.txt
- pyproject.toml / setup.cfg / setup.py

---

## 開発・貢献
- まずは README とこの構成に沿って各モジュールを実装してください。
- テスト（ユニット・統合）を追加し、CI（GitHub Actions など）で自動実行することを推奨します。
- 実取引に接続する場合は、必ずテスト/サンドボックス環境で十分に検証してください。金銭的リスクが伴います。

---

必要であれば、以下の追加ドキュメントを作成します:
- 実際のデータ取得/注文 API のサンプル実装
- サンプル戦略（例: 単純移動平均クロス戦略）のコード
- テストケースと CI 設定
- デプロイ/運用手順（コンテナ化 / systemd / supervisor）

どの部分の詳細が必要か教えてください。具体的な実装例やサンプルコードも作成できます。