KabuSys
=======

KabuSys は日本株の自動売買システム向けの骨組み（スケルトン）パッケージです。データ取得、売買戦略、注文執行、監視（モニタリング）の各コンポーネントを分離した構造になっており、独自の戦略や取引所（証券会社）API のアダプタを組み込んで拡張できます。

現在のバージョン: 0.1.0

主な目的
- 自動売買システムの基本構造を提供して、独自ロジックの実装を容易にする
- データ取得・戦略・注文執行・監視をモジュールごとに分割して責務を明確化する
- 実装のひな形（テンプレート）として利用できるようにする

機能一覧
- パッケージ骨組み（モジュール分割）
  - data: マーケットデータ取得・履歴データ処理用のインターフェース
  - strategy: 売買戦略（シグナル生成）を実装するための場所
  - execution: 証券会社API（注文）や発注ロジックのアダプタを実装するための場所
  - monitoring: ログ、メトリクス、アラート、ダッシュボードなどの監視機構のための場所
- バージョン情報（__version__ = "0.1.0"）
- パッケージの公開・インポート用の構成（src-layout）

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone <repository-url>
   - cd <repository-root>

2. Python 仮想環境を作成・有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 開発中はローカル編集を反映させるために編集可能インストール:
     - pip install -e .

4. （任意）テスト・静的解析のセットアップ
   - pytest, flake8, black などを requirements-dev.txt に追加して運用してください。

環境変数（例）
- 実際の取引・API 呼び出しを行う場合は、証券会社の API キー等を環境変数で管理することを推奨します（例）:
  - KABU_API_KEY
  - KABU_API_SECRET
  - KABU_ACCOUNT_ID

使い方（導入例）
- 最小限の利用例（バージョン確認）:

  python
  >>> import kabusys
  >>> print(kabusys.__version__)
  0.1.0

- 拡張の方針（概念的な例）
  - 各モジュールは「インターフェース（抽象クラス）」を定義して、それを実装する具象クラスを作る想定です。
  - 例: strategy パッケージに BaseStrategy（＝決定メソッドを持つ抽象クラス）を定義し、ユーザー側はそれを継承して独自戦略を実装します。
  - 同様に data パッケージには MarketDataClient、execution には OrderExecutor、monitoring には MonitorClient といったインターフェースを用意すると使いやすくなります。

- 具体例（擬似コード: 実際のクラスは未実装のため、作成して使ってください）:

  # my_strategy.py（例）
  from kabusys import data, strategy, execution, monitoring

  class MyStrategy(strategy.BaseStrategy):            # BaseStrategy を実装する想定
      def on_tick(self, market_snapshot):
          # シグナル生成ロジック
          return "BUY"  # または "SELL" / None

  def main():
      md_client = data.YourMarketDataClient(...)
      executor = execution.YourOrderExecutor(...)
      monitor = monitoring.YourMonitorClient(...)
      strat = MyStrategy(...)

      # 簡易ループ（擬似）
      for snapshot in md_client.stream("7203"):  # 銘柄コード 7203 など
          signal = strat.on_tick(snapshot)
          if signal == "BUY":
              executor.send_order(symbol="7203", side="BUY", qty=100)
          monitor.record(snapshot, signal)

- 注意: 上記は実装方針の例です。現状のリポジトリには具体的な実装（BaseStrategy, YourMarketDataClient 等）は含まれていないため、必要に応じて各モジュールにクラスを作成してください。

ディレクトリ構成
（現状の src 配下の構成）

- src/
  - kabusys/
    - __init__.py           （パッケージ初期化、__version__ を定義）
    - data/                 （マーケットデータ用モジュール - 空ディレクトリ）
      - __init__.py
    - strategy/             （戦略用モジュール - 空ディレクトリ）
      - __init__.py
    - execution/            （注文執行用モジュール - 空ディレクトリ）
      - __init__.py
    - monitoring/           （監視用モジュール - 空ディレクトリ）
      - __init__.py

開発ガイド（推奨）
- インターフェース設計
  - 各サブパッケージに抽象ベースクラス（ABC）を定義して、明確な契約（API）を用意します。
  - 例: strategy.BaseStrategy, data.MarketDataClient, execution.OrderExecutor, monitoring.Monitor

- 設定管理
  - YAML/JSON/ENV を用いて接続情報や戦略パラメータを分離してください。
  - シークレット情報（APIキー等）は環境変数かシークレットマネージャ経由で管理すること。

- テスト
  - 戦略はユニットテストでロジックを検証できるように、マーケットデータのフェイクやモックを用意してください。
  - execution の実コードはテスト時にモック化してリアル注文が飛ばないようにすること。

- ロギング・監視
  - 重要なイベント（注文送信、注文約定、例外）は構造化ログとして出力し、早期検知のためのアラートを設定してください。

拡張例アイデア
- 複数の証券会社 API を統一インターフェースで扱える adaptor を作る
- バックテスト用モジュール（ヒストリカルデータ再生）
- リスク管理モジュール（全体ポジション、取引制限）
- Web UI / ダッシュボードで戦略の状態を可視化

貢献
- Issue や Pull Request は歓迎します。Pull Request を送る際はできるだけ小さな単位で、変更の理由を明確にしてください。

免責事項
- 本リポジトリは学習・開発用の骨組みです。実際の資金を用いた運用を行う前に、十分なテストと安全対策を行ってください。取引による損失については責任を負いません。

以上

（必要に応じて README に API 仕様やサンプル実装、CI 設定、依存ファイル（requirements.txt）などを追加してください。）
