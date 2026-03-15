KabuSys
=======

KabuSys は、日本株の自動売買（アルゴリズムトレード）を想定した軽量な骨組み（フレームワーク）です。  
このリポジトリは、データ取得、戦略ロジック、注文実行、監視・通知といった主要コンポーネントをパッケージ分割したテンプレート実装を提供します。実際の取引ロジックやブローカー連携はユーザーが実装して拡張する想定です。

主な目的
- 自動売買システム構築のためのプロジェクトテンプレートを提供する
- 各機能（データ取得、戦略、実行、監視）を責務ごとに分離して実装しやすくする
- 独自の取引戦略やブローカーAPIに容易に接続できる構造を提供する

機能一覧
- パッケージ化されたモジュール構成（data / strategy / execution / monitoring）
  - data: 市場データの取得・前処理用のインターフェースを置く場所
  - strategy: 売買シグナルやポジション管理のロジックを置く場所
  - execution: 注文送信や約定確認などブローカー連携の実装を置く場所
  - monitoring: ログ、アラート、ダッシュボード連携など監視用処理を置く場所
- プロジェクトのバージョン情報（src/kabusys/__init__.py の __version__）

セットアップ手順
1. 必要条件
   - Python 3.8 以上を推奨
   - git

2. リポジトリのクローン
   ```
   git clone <リポジトリのURL>
   cd <リポジトリ名>
   ```

3. 仮想環境の作成（推奨）
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

4. 開発インストール
   - プロジェクトルートで（setup.py / pyproject.toml がある場合）:
     ```
     pip install -e .
     ```
   - 依存パッケージがある場合は requirements.txt を用意している想定です:
     ```
     pip install -r requirements.txt
     ```

5. （任意）開発ツール
   - linters, type checker, test runner 等を追加する場合は適宜 pip でインストールしてください。

使い方（テンプレートとサンプル）
このリポジトリは各モジュールの骨組みを提供します。実際の利用では各モジュールに具体的な関数やクラスを実装します。以下は実装例のテンプレートです。

- 基本的なモジュールの呼び出し例（実装は各自で追加してください）
  ```
  from kabusys import data, strategy, execution, monitoring

  # 1) データ取得（data モジュールに実装）
  prices = data.fetch_price("7203", start="2024-01-01", end="2024-02-01")

  # 2) シグナル生成（strategy モジュールに実装）
  signal = strategy.generate_signal(prices)

  # 3) 注文実行（execution モジュールに実装）
  if signal == "BUY":
      execution.send_order(symbol="7203", side="BUY", qty=100)

  # 4) 監視・通知（monitoring モジュールに実装）
  monitoring.notify("注文を送信しました: 7203 BUY 100")
  ```

- 推奨される責務分離（例）
  - data:
    - fetch_price(symbol, start, end) → pandas.DataFrame を返す
    - preprocess(df) → 戦略が扱いやすい形に整形
  - strategy:
    - Strategy クラスを定義し、 decide(current_data) → "BUY"/"SELL"/"HOLD" を返す
    - backtest(history, strategy) → バックテスト結果を返す（オプション）
  - execution:
    - BrokerClient クラスを実装し、 send_order / cancel_order / get_position などを提供
    - 実行は安全のため非同期やリトライを組み込むことを推奨
  - monitoring:
    - ログ出力、メール/SNS/Slack 通知、簡易ウェブダッシュボードなどを実装

注意事項
- 実際の金銭が関わる取引の実装・テストは十分に注意して行ってください。損失が発生する可能性があります。
- ブローカーAPIキーや秘密情報は環境変数や安全なシークレット管理を利用してください。ソース管理に直接書き込まないでください。

ディレクトリ構成
（このリポジトリの現状のファイル構成）
- src/
  - kabusys/
    - __init__.py                    # パッケージ本体（__version__ を定義）
    - data/
      - __init__.py                  # データ取得モジュール（実装場所）
    - strategy/
      - __init__.py                  # 戦略ロジックモジュール（実装場所）
    - execution/
      - __init__.py                  # 注文実行モジュール（実装場所）
    - monitoring/
      - __init__.py                  # 監視・通知モジュール（実装場所）

拡張・貢献
- 各サブパッケージ（data, strategy, execution, monitoring）に具体的な実装を追加していくことで機能を拡張してください。
- Pull Request / Issue ベースでの改善提案を歓迎します。特に、テスト、サンプル戦略、ブローカー接続ラッパー（例: kabuステーション API など）の追加は有益です。

ライセンス
- 特定のライセンスファイルがない場合、商用利用や再配布に関する制約が不明です。公開する場合は LICENSE ファイルを追加してください。

最後に
このリポジトリは自動売買システムの「骨組み」を提供することを目的としています。実際の運用には多くの追加実装（堅牢な注文管理、エラーハンドリング、バックテスト、リスク管理、ログ・監視）が必要です。安全第一で開発を進めてください。