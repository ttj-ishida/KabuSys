# KabuSys — 日本株自動売買システム

KabuSys は日本株の自動売買を想定した軽量なライブラリ骨組みです。モジュールを分離しており、データ取得、売買戦略、注文実行、監視（ログ・メトリクス）をそれぞれ独立して実装・拡張できる設計になっています。

現在のバージョン: 0.1.0

---

## プロジェクト概要

このプロジェクトは以下の目的で作られています。

- 日本株の自動売買ロジックを整理して実装できる土台を提供する
- データ取得（market data）、戦略（strategy）、実行（execution）、監視（monitoring）という関心事の分離により拡張性を確保する
- 実運用に向けた各モジュールの接続点（インターフェース）を明確にする

現状はパッケージ構成と基本的なモジュールプレースホルダのみを含み、具体的な外部APIの実装や取引プロバイダ接続はユーザが導入することを想定しています。

---

## 機能一覧

本テンプレートに含まれる主要モジュール（インターフェース）:

- data
  - 市場データ（株価・板情報・約定履歴など）を取得・整形するための領域
  - 例：CSV/DB/HTTP/WebSocket などからの取り込み用インターフェース
- strategy
  - 取得したデータを元に売買シグナルを生成するロジックを配置する領域
  - 例：テクニカル指標、裁定、アルゴリズムトレード戦略など
- execution
  - 注文の発行・管理（発注・キャンセル・約定確認）を扱う領域
  - 例：証券会社API（kabuステーション等）やシミュレーション環境への接続
- monitoring
  - ログ出力／アラート／統計（P&L、ドローダウンなど）を扱う領域
  - 例：Prometheus メトリクス、ログ集約、可視化フックなど

注意: 現状はインターフェース・パッケージのみで、具体的実装は含まれていません。各機能はプロジェクト要件に応じて実装してください。

---

## セットアップ手順

以下は開発環境でソースから使い始めるための一般的な手順例です。

1. 前提
   - Python 3.8 以上を推奨（プロジェクト要件に合わせて調整してください）
   - 仮想環境の利用を推奨（venv / virtualenv / conda 等）

2. リポジトリをクローン（例）
   ```
   git clone <リポジトリURL>
   cd <リポジトリ名>
   ```

3. 仮想環境の作成と有効化（venv の例）
   ```
   python -m venv .venv
   source .venv/bin/activate     # macOS / Linux
   .venv\Scripts\activate        # Windows
   ```

4. インストール（開発用に編集可能インストール）
   - プロジェクトに setuptools / pyproject.toml / setup.py がある前提で:
     ```
     pip install -e .
     ```
   - 依存関係が別途ある場合は requirements.txt を用意して:
     ```
     pip install -r requirements.txt
     ```

5. 設定
   - 実際の取引やデータ取得には外部APIキーやエンドポイント設定が必要です。環境変数・設定ファイル（例: config.yaml）等を用いて管理してください。
   - 例（環境変数）:
     ```
     export KABU_API_KEY="your_api_key"
     export KABU_API_SECRET="your_api_secret"
     ```

---

## 使い方

以下は最小限の利用例（パッケージの確認や基本的な流れ）です。実運用向けの実装は各モジュールに応じて作成してください。

1. パッケージ情報の確認
   ```python
   import kabusys
   print(kabusys.__version__)   # -> "0.1.0"
   ```

2. モジュールをインポート（プレースホルダ）
   ```python
   from kabusys import data, strategy, execution, monitoring

   # 各モジュールに実装されたクラス/関数を使用する想定
   # 例（擬似コード）:
   # market = data.MarketDataClient(...)
   # strat = strategy.MyStrategy(...)
   # exec_client = execution.BrokerClient(...)
   # monitor = monitoring.Monitor(...)
   #
   # while True:
   #     bar = market.get_latest_bar("7203.T")
   #     signal = strat.on_bar(bar)
   #     if signal == "BUY":
   #         exec_client.place_order("7203.T", size=100, side="BUY")
   #     monitor.record(...)
   ```

3. 実稼働に向けての注意
   - 注文実行は本番環境では十分な検証（ペーパートレード・サンドボックス）を行ってください。
   - エラーハンドリング、レート制限、再接続戦略、ログ保存、資金管理ルールは必須です。
   - テスト（単体テスト／統合テスト）を整備してから運用してください。

---

## ディレクトリ構成

現在の主要なファイル・ディレクトリ構成（抜粋）は以下の通りです。

- src/
  - kabusys/
    - __init__.py            # パッケージ定義（version, __all__）
    - data/
      - __init__.py          # data モジュール用プレースホルダ
    - strategy/
      - __init__.py          # strategy モジュール用プレースホルダ
    - execution/
      - __init__.py          # execution モジュール用プレースホルダ
    - monitoring/
      - __init__.py          # monitoring モジュール用プレースホルダ

README.md（本ファイル）

※ 実際のプロジェクトでは以下の追加ファイルが一般的です：
- setup.py / pyproject.toml
- requirements.txt
- tests/（単体テスト）
- examples/（実行例スクリプト）
- docs/（ドキュメント）

---

必要に応じて、各モジュールのインターフェース（クラス / 関数）のテンプレート作成や、外部証券API(kabuステーション等)との接続サンプルを追記できます。どの程度の具体実装が必要か教えていただければ、サンプルコードや設定ファイル例を作成します。