# KabuSys

日本株の自動売買システム（スケルトン実装）

バージョン: 0.1.0

概要
- KabuSys は日本株の自動売買システムを構築するためのコアパッケージのスケルトンです。
- データ取得、売買戦略、注文実行、監視（ログ・メトリクス）を役割ごとに分離したモジュール構成になっています。
- ここに含まれるのは基本的なパッケージ骨格で、各モジュールに実際の実装（API クライアント、戦略ロジック、注文フロー、監視機能）を追加していきます。

主な機能（予定／想定）
- 株価や板情報などのマーケットデータ取得（data）
- 売買戦略の実装・評価（strategy）
- 注文送信、注文管理（execution）
- 実行状況やアラートの監視・記録（monitoring）
- 各機能は独立しており、テストや差し替えがしやすい設計を想定

セットアップ手順

前提
- Python 3.8 以上を推奨
- 実際の運用では証券会社の API（例：kabuステーション等）情報や API キーが必要になります。ここではその取得手順は含みません。

ローカルでの開発・動作確認手順（推奨）
1. リポジトリをクローン
   git clone <リポジトリURL>
   cd <リポジトリ>

2. 仮想環境の作成（例）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell では .venv\Scripts\Activate.ps1)

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     pip install -r requirements.txt
   - パッケージとして編集可能にインストールする場合（pyproject.toml / setup.py がある場合）:
     pip install -e .
   - まだパッケージ設定が無い場合は、開発中はプロジェクトの src ディレクトリを PYTHONPATH に追加して利用できます:
     export PYTHONPATH="$(pwd)/src:$PYTHONPATH"  # macOS / Linux
     set PYTHONPATH=%cd%\src;%PYTHONPATH%         # Windows（cmd）

4. 環境変数 / 設定
   - 実際の API キーやエンドポイントは環境変数や設定ファイルで管理してください（例: KABU_API_KEY, KABU_API_ENDPOINT）。
   - サンプル:
     export KABU_API_KEY="あなたのAPIキー"
     export KABU_API_ENDPOINT="https://api.example.com"

使い方（最小例）
- パッケージは以下の名前空間を提供します:
  from kabusys import __version__, data, strategy, execution, monitoring

- 開発時には各モジュールに実際のクラスや関数を実装します。例（概念的なサンプル）:

  - data モジュール
    - MarketDataClient クラスを実装して株価や板情報を取得

  - strategy モジュール
    - Strategy 抽象クラスを定義し、シグナル生成メソッド（generate_signal）などを実装

  - execution モジュール
    - ExecutionClient を実装して注文送信、約定確認、注文取消などを行う

  - monitoring モジュール
    - ロギングやメトリクス送信、アラート通知を実装

- 簡単な実行フロー（擬似コード）
  1. data.MarketDataClient で市場データを取得
  2. strategy.MyStrategy にデータを渡して売買シグナルを生成
  3. execution.ExecutionClient で注文を送信
  4. monitoring でログ・ステータスを記録

ディレクトリ構成
（このリポジトリの現状）
- src/
  - kabusys/
    - __init__.py            # パッケージメタ（バージョン、公開 API）
    - data/
      - __init__.py          # データ取得関連モジュールを配置
    - strategy/
      - __init__.py          # 戦略ロジックを配置
    - execution/
      - __init__.py          # 注文実行関連を配置
    - monitoring/
      - __init__.py          # 監視・ログ関連を配置

開発ノート / 実装のヒント
- 各モジュールはインターフェース（抽象クラスやプロトコル）を定義して実装を差し替えやすくすることを推奨します（単体テストの容易化）。
- 実運用を考慮する場合は、以下を検討してください：
  - 冪等な注文管理と障害復旧（リトライ、トランザクション的な注文処理）
  - リアルタイム監視とアラート（Slack、メール等）
  - 履歴データの保存（時系列 DB、パラquetなど）
  - バックテスト用のインターフェース（戦略の検証）

ライセンス / 責任
- 本リポジトリは自動売買のスケルトンです。実際に資金を投入して取引を行う前に徹底したテストとレビューを行ってください。
- 金融取引に伴うリスクはユーザーに帰属します。実運用前に法的・規制面の確認も行ってください。

貢献
- Issue / PR は歓迎します。機能追加（データコネクタ、戦略テンプレート、実行バックエンド）、ドキュメント改善などをお願いします。

お問い合わせ
- 実装や拡張の相談、設計レビューなどが必要な場合は issue を立ててください。