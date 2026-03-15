KabuSys
=======

KabuSys は日本株の自動売買（アルゴリズムトレード）を想定した軽量な Python パッケージの骨組みです。  
このリポジトリはデータ取得、売買戦略、発注実行、監視のためのサブパッケージを含むモジュール構成を提供します。現時点では骨組みのみで、各機能は利用者が実装して拡張することを想定しています。

バージョン: 0.1.0

主な目的
- 日本株向け自動売買システムのベースライン実装（アーキテクチャ）を提供
- データ取得、戦略ロジック、発注実行、監視の責務を分割した構成を提供
- 既存の証券 API やバックテストフレームワークとの接続の起点を提供

機能一覧
- パッケージ構成（モジュール分割）
  - kabusys.data: 価格・板情報などのデータ取得・整形用
  - kabusys.strategy: 売買戦略（シグナル生成）を実装する場所
  - kabusys.execution: 実際の発注ロジック（API 呼び出しや注文管理）
  - kabusys.monitoring: ログ、アラート、稼働状況の監視
- パッケージ情報（__version__ の提供）
- 開発・拡張のための雛形コード

セットアップ手順
1. リポジトリをクローン
   - git clone <このリポジトリの URL>
   - cd <リポジトリ名>

2. 仮想環境の作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール
   - 開発中にローカル編集を反映させたい場合（推奨）
     - pip install -e .
       ※ プロジェクトに pyproject.toml または setup.py があることを前提とします。無ければ、直接パスを PYTHONPATH に追加するか、上記のファイルを作成してください。
   - 代替（ファイル構成のみで利用する一時的な方法）
     - export PYTHONPATH=$PWD/src    (Windows: set PYTHONPATH=%CD%\src)

4. 依存パッケージ
   - 現在の雛形には外部依存がありません。実装に応じて、requests、pandas、numpy、websocket-client 等を追加してください。

注意: 実際に証券会社の API を叩いて発注する場合は、API キーや秘密情報の管理、テスト環境（デモ/サンドボックス）の使用、レート制限や例外処理の実装、リスク管理を必ず行ってください。

基本的な使い方
- パッケージ情報の確認
  Python REPL やスクリプトからバージョンを確認できます。
  - 例:
    - import kabusys
    - print(kabusys.__version__)

- 開発の流れ（概念例）
  1. kabusys.data にデータ取得用のクラス/関数を実装する
  2. kabusys.strategy にシグナル生成ロジック（買い・売り判定）を実装する
  3. kabusys.execution に注文実行クラスを実装し、取引所／証券 API と接続する
  4. kabusys.monitoring にログ出力や通知（Slack / Email 等）を実装する
  5. これらを統合するランナー（main）を作成し、定期実行やスケジューリングを行う

- サンプル（骨組み）: 各モジュールの利用イメージ
  - data の例（擬似コード）
    - from kabusys.data import MarketDataClient
    - md = MarketDataClient(api_key=...)
    - price = md.get_last_price("7203")  # 銘柄コード 7203（トヨタ）

  - strategy の例（擬似コード）
    - from kabusys.strategy import StrategyBase
    - class SimpleMA(StrategyBase):
          def generate_signal(self, prices):
              # 移動平均を使った単純な売買シグナルを返す
              return "BUY" or "SELL" or "HOLD"

  - execution の例（擬似コード）
    - from kabusys.execution import Executor
    - exec = Executor(api_client=...)
    - exec.place_order(symbol="7203", side="BUY", size=100)

  - monitoring の例（擬似コード）
    - from kabusys.monitoring import Monitor
    - mon = Monitor()
    - mon.log("注文を発注しました: 7203 BUY 100")

- 注意: 上記は設計例です。実際のメソッド名・クラス名は利用者が自由に決め、実装してください。

ディレクトリ構成
プロジェクトルートの代表的な構成（現状のファイルを元に記載）:

- src/
  - kabusys/
    - __init__.py          # パッケージ情報（__version__ など）
    - data/
      - __init__.py        # データ取得モジュール（実装場所）
    - strategy/
      - __init__.py        # 戦略ロジック（実装場所）
    - execution/
      - __init__.py        # 発注・実行ロジック（実装場所）
    - monitoring/
      - __init__.py        # 監視・ログ関連（実装場所）

例（ツリー表示）
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

拡張・実装のヒント
- 単体テスト: 各サブパッケージに対して pytest によるユニットテストを用意することを推奨します。特に発注まわりはモックを活用して実環境への不要なアクセスを防ぎます。
- 設定管理: API キーやトークンは環境変数、Vault、もしくは暗号化された設定ファイルに保管してください。平文のコードに直接書かないでください。
- ロギング: 標準 logging モジュールを使い、ログレベルや出力先（ファイル/コンソール/外部サービス）を設定しましょう。
- バックテスト: strategy はバックテスト可能なインターフェース（履歴データを渡してシグナルを得る）にしておくと便利です。
- リスク管理: 発注サイズ、日中の最大建玉、システム停止条件などの安全策を必ず組み込んでください。

貢献について
- バグ報告、機能要望、プルリクエストは歓迎します。Issue を立ててから実装するワークフローを推奨します。
- コード規約: PEP8 準拠（flake8 等）を目安にしてください。

ライセンス
- 明示的なライセンスファイルがない場合は、使用条件を明確にするために LICENSE を追加してください（例: MIT License 等）。

最後に
このリポジトリは自動売買システムの雛形です。実際に資金を扱う際は十分なテストとリスク管理を行ってください。必要であれば、各サブパッケージのテンプレート（サンプル実装）も提供できます。どの部分を最初に実装したいか教えてください。