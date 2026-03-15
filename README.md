# KabuSys

日本株自動売買システムの骨格ライブラリです。  
このリポジトリはシステムを機能別に分割したパッケージ構成（データ取得、売買ロジック、注文実行、監視）を提供します。現状はプロジェクトの初期スケルトンで、各モジュールの実装を追加していくことを想定しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株の自動売買システムを構築するためのモジュール群のひな形です。主要な役割を責務ごとに分割し、拡張・テスト・保守がしやすい構造を目指しています。

主要パッケージ:
- data: 市場データの取得・整形（ティック、板、OHLC 等）
- strategy: 売買戦略・シグナル生成
- execution: 注文送信・約定管理
- monitoring: ログ、メトリクス、ダッシュボードやアラート

---

## 機能一覧（想定・骨子）

- データ取得インターフェース（証券会社APIやCSV読み込み等の抽象化）
- 戦略モジュール（シグナル生成の基底クラスを想定）
- 注文実行モジュール（注文送信、注文状態の追跡）
- 監視モジュール（トレードログ、ポートフォリオ、アラート出力）
- パッケージ化済み（Pythonパッケージとして利用可能な構成の開始点）

> 注: 現時点のソースはモジュールのパッケージ構成のみで、具体的な実装は含まれていません。各モジュールにクラスや機能を実装していくことを想定しています。

---

## セットアップ手順

1. Python 環境（推奨: 3.8 以上）を準備します。

2. 仮想環境の作成（推奨）
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .\.venv\Scripts\activate

3. pip を最新化
   - pip install --upgrade pip

4. リポジトリから利用する方法（2通り）

   a) パッケージが setuptools/pyproject で構成されている場合（将来的な方法）:
   - プロジェクトルートで:
     - pip install -e .

   b) 現状の最小構成で実行する場合:
   - 簡易的に src を PYTHONPATH に追加して利用:
     - PYTHONPATH=src python -c "import kabusys; print(kabusys.__version__)"
     - Windows (PowerShell): $env:PYTHONPATH = "src"; python -c "import kabusys; print(kabusys.__version__)"

5. 依存ライブラリが増えた場合は requirements.txt を追加して:
   - pip install -r requirements.txt

---

## 使い方（例・骨組み）

以下はパッケージを利用する最小の例（実装を追加することで動作します）:

- バージョン確認
  - python -c "import kabusys; print(kabusys.__version__)"

- モジュールの基本的な利用イメージ（擬似コード）:

  ```python
  from kabusys import data, strategy, execution, monitoring

  # データ取得（実装を追加）
  # datasource = data.YourDataSource(api_key=..., symbols=[...])
  # price_df = datasource.get_ohlcv(...)

  # 戦略（実装を追加）
  # strat = strategy.YourStrategy(param1=..., param2=...)
  # signals = strat.generate_signals(price_df)

  # 注文実行（実装を追加）
  # executor = execution.OrderExecutor(api_client=...)
  # for sig in signals:
  #     executor.send_order(sig)

  # 監視（実装を追加）
  # monitor = monitoring.Monitor()
  # monitor.record_trade(...)
  # monitor.report()
  ```

- 実装のヒント
  - data パッケージ: 抽象基底クラス（BaseDataSource）を用意し、証券会社APIやCSV/DBからの取得クラスを派生。
  - strategy パッケージ: 戦略基底（BaseStrategy）で入力（価格等）→ 出力（買い/売り/ホールド）を統一。
  - execution パッケージ: OrderExecutor 等で送信・キャンセル・注文状態管理を実装。
  - monitoring パッケージ: ログ出力・メトリクス収集・通知（メール/Slack）などを実装。

---

## ディレクトリ構成

現状のファイル構成:

- src/
  - kabusys/
    - __init__.py          — パッケージ初期化（バージョン情報: 0.1.0）
    - data/
      - __init__.py        — データ関連モジュール（未実装）
    - strategy/
      - __init__.py        — 戦略関連モジュール（未実装）
    - execution/
      - __init__.py        — 注文実行関連モジュール（未実装）
    - monitoring/
      - __init__.py        — 監視関連モジュール（未実装）

各パッケージの役割:
- kabusys/__init__.py
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]

---

## 開発・拡張ガイド（簡潔）

- 新しい機能を追加する際は、該当するサブパッケージ（data/ strategy/ execution/ monitoring）にモジュールを追加してください。
- テストは tests/ ディレクトリに配置し、pytest 等で実行することを推奨します。
- パブリックAPI（外部に公開するクラス・関数）はサブパッケージの __all__ に明記してください。
- 外部API（証券会社など）と連携する際は API キー等の機密情報を直接ソースに書かず、環境変数や設定ファイル（.env）で管理してください。

---

README はこのリポジトリの初期ドキュメントです。さらに具体的な実装（クラス、関数、例）を追加した際に、使用例や API リファレンスを拡充してください。必要があれば、サンプル戦略や統合テストのテンプレートも作成することをおすすめします。