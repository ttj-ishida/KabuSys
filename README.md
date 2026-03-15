KabuSys
=======

KabuSys は日本株の自動売買システムを想定した軽量なパッケージ構成です。現在はパッケージのスケルトン（モジュール分割とバージョン情報のみ）が用意されています。今後、データ取得、売買戦略、注文実行、監視機能を順次実装していくためのベースとなります。

プロジェクト概要
---------------
- 名前: KabuSys
- 概要: 日本株を対象とした自動売買システムのライブラリ構成（data / strategy / execution / monitoring）
- バージョン: 0.1.0（src/kabusys/__init__.py に定義）
- 目的: モジュール分離された拡張しやすい自動売買フレームワークの提供

主な機能（予定 / 構成）
--------------------
- data: 市場データの取得・整形・保存（CSV、API、バックテスト用データ等）
- strategy: 売買戦略（シグナル生成、ポジション管理、パラメータ最適化）
- execution: 注文発行・約定管理・取引所／証券会社 API のラッパー
- monitoring: 稼働状況、パフォーマンス、ログやダッシュボードの監視

現状のコードベースは各パッケージの初期化ファイルのみを含んでおり、個別モジュール（機能実装）は未実装です。README に示す使い方は導入例・開発時の参照例です。

セットアップ手順
----------------

前提
- Python 3.8 以上を推奨（実装内容により要件は変動します）

開発環境（ソースから実行する場合）
1. リポジトリをクローン
   - git clone <リポジトリURL>
2. 仮想環境の作成（任意）
   - POSIX (macOS / Linux)
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell)
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1
3. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - （現状依存は定義されていません。必要に応じて追加してください）
4. ソースを Python の import パスに含める
   - プロジェクトルートには src/ ディレクトリがあり、その中に kabusys パッケージがあります。実行時に src を PYTHONPATH に追加してください。
   - POSIX:
     - export PYTHONPATH="$(pwd)/src:${PYTHONPATH:-}"
   - Windows (PowerShell):
     - $env:PYTHONPATH = (Resolve-Path .\src).Path + ";" + $env:PYTHONPATH

注: 将来的には pyproject.toml / setup.cfg / setup.py を追加して pip install -e . に対応させることを推奨します。

使い方（例）
------------

以下は、現状のパッケージ構成を使って簡単にインポートする例です。実際の機能（関数・クラス）は未実装のため、実装時に置き換えてください。

1) バージョン確認
- POSIX あるいは Windows で PYTHONPATH を設定後:
  - python -c "import kabusys; print(kabusys.__version__)"
  - 出力例: 0.1.0

2) 想定されるワークフローの擬似コード（実装例）
- これはあくまで設計上の使用例です。各モジュールの API は今後定義されます。

  ```python
  from kabusys import data, strategy, execution, monitoring

  # データ取得（例: CSV から読み込む）
  # market_data = data.load_csv("market.csv")  # ← 実装予定

  # 戦略初期化
  # strat = strategy.SimpleMovingAverage(window_short=5, window_long=25)

  # シグナル生成
  # signals = strat.generate_signals(market_data)

  # 注文実行
  # executor = execution.Executor(api_key="...", api_secret="...")
  # executor.place_orders(signals)

  # 監視開始
  # monitoring.start_dashboard(port=8080)
  ```

3) 開発時のテスト実行（将来的な想定）
- pytest などのテストフレームワークを導入する場合:
  - pip install pytest
  - pytest tests/

ディレクトリ構成
----------------

現在のリポジトリはシンプルなパッケージ構成です。以下は主要ファイルと想定ツリーです。

- src/
  - kabusys/
    - __init__.py         # パッケージのバージョン / __all__ 定義（現状あり）
    - data/
      - __init__.py       # データ関連モジュール（未実装）
    - strategy/
      - __init__.py       # 戦略関連モジュール（未実装）
    - execution/
      - __init__.py       # 注文実行関連モジュール（未実装）
    - monitoring/
      - __init__.py       # 監視関連モジュール（未実装）

開発・拡張ガイド（短く）
-----------------------
- 各サブパッケージに機能別モジュール（例: data/csv.py, strategy/sma.py, execution/kabus_handler.py, monitoring/web.py）を追加してください。
- API キーやシークレットなどの機密情報は、環境変数や設定ファイル（git に含めない）で管理すること。
- 本番注文実行コードは冪等性・例外処理・ログ・テストを厳密に整備してから運用すること。
- 単体テスト・インテグレーションテストを用意し、CI で自動実行するのを推奨します。

今後の予定（例）
----------------
- データ取得モジュールの実装（CSV、QUICK、各種 API）
- 代表的な戦略の実装（移動平均、RSI、ボリンジャーバンド 等）
- 注文実行のための証券会社 API ラッパー実装（kabuステーション等）
- 監視用ダッシュボード・アラート機能の実装
- ドキュメント整備、サンプル戦略の追加

貢献・問い合わせ
-----------------
- イシューやプルリクエストを歓迎します。まずは Issue を立てて実装方針を相談してください。
- 機能追加や API 設計に関しては、互換性を考慮した上で説明を付けて PR を作成してください。

本 README は現在のソース（スケルトン）に基づくもので、実機能は順次実装されます。必要ならば README に含める具体的な使用例や CI / packaging のテンプレートを追加で作成します—その場合はどの形式（pyproject.toml など）にしたいか教えてください。