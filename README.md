# KabuSys

日本株自動売買システムのための軽量パッケージ（骨組み）。  
このリポジトリはシステムを構成する主要コンポーネント（データ取得、戦略、注文実行、モニタリング）の雛形を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築のためのモジュール化されたパッケージ雛形です。  
各機能（データ取得、戦略、注文実行、モニタリング）を分離して実装できるように設計されており、具体的なブローカーAPIや戦略ロジックは各モジュール内で実装します。

目的：
- 自動売買アルゴリズムの開発／テストを容易にする雛形を提供する
- コンポーネントを分離して保守性を高める
- 実装例を各チーム・個人に合わせて拡張しやすくする

---

## 機能一覧（想定）

- data: 市場データの取得・整形（板情報、約定履歴、日次/分次OHLC 等）
- strategy: 売買戦略の定義とシグナル生成
- execution: ブローカーAPIを通した注文送信・約定管理（成行/指値/キャンセル 等）
- monitoring: ログ、パフォーマンス指標、アラート、ダッシュボード連携

※ 現状はモジュールの雛形のみです。各モジュール内部に具体的な実装（APIクライアント、戦略クラスなど）を追加してください。

---

## セットアップ手順

前提
- Python 3.8 以上を推奨
- 仮想環境の利用を推奨（venv / conda 等）

手順例（Unix 系 / Windows PowerShell での一般的な流れ）:

1. リポジトリをクローン
   - git clone <REPO_URL>
   - cd <repo>

2. 仮想環境作成・有効化（例: venv）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows(PowerShell): .venv\Scripts\Activate.ps1

3. 依存関係のインストール
   - requirements.txt があれば: pip install -r requirements.txt
   - （現状では依存ファイルが含まれていないため、必要なライブラリをプロジェクトに応じて追加してください）

4. ローカルで使う方法（パッケージとして扱う / 開発モード）
   - プロジェクトをパッケージ化している場合:
     - pip install -e .
   - パッケージ化していない場合（簡易）:
     - PYTHONPATH を設定して src を参照させる
       - Unix/macOS: export PYTHONPATH=$(pwd)/src:$PYTHONPATH
       - Windows(PowerShell): $env:PYTHONPATH = (Resolve-Path .\src).Path + ";" + $env:PYTHONPATH

---

## 使い方（基本例）

まずはパッケージを import してバージョンやモジュールが読み込めることを確認します。

Python シェルやスクリプトで:

```python
import kabusys
print(kabusys.__version__)   # 0.1.0

import kabusys.data
import kabusys.strategy
import kabusys.execution
import kabusys.monitoring
```

各モジュールは雛形として存在するため、以下のような役割でクラスや関数を実装してください（例は設計例）:

- data モジュールの例（擬似コード）
  - MarketDataClient クラス: get_ohlc(symbol, timeframe), get_ticker(symbol) など

- strategy モジュールの例
  - BaseStrategy クラス: on_bar(bar)、generate_signals() などを実装し、派生クラスでロジック実装

- execution モジュールの例
  - ExecutionClient クラス: send_order(order)、cancel_order(order_id)、get_positions() などを実装（kabuステーション等のAPIラッパー）

- monitoring モジュールの例
  - Monitor クラス: log_trade(trade)、export_metrics()、raise_alert() など

サンプルワークフロー（擬似コード）:

```python
# 1. データ取得
md = kabusys.data.MarketDataClient(...)
bars = md.get_ohlc("7203.T", timeframe="1m", count=100)

# 2. 戦略実行
strategy = MyStrategy(...)
signals = strategy.generate_signals(bars)

# 3. 注文実行
exec_client = kabusys.execution.ExecutionClient(...)
for sig in signals:
    exec_client.send_order(sig)

# 4. モニタリング
monitor = kabusys.monitoring.Monitor(...)
monitor.log_trade(...)
```

注: 上記クラスはサンプルであり、実装は本リポジトリの各モジュールに追加してください。

---

## ディレクトリ構成

現状の主要ファイル/ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py        # パッケージのエントリ（version, __all__）
    - data/
      - __init__.py      # data モジュール（市場データ取得）
    - strategy/
      - __init__.py      # strategy モジュール（戦略ロジック）
    - execution/
      - __init__.py      # execution モジュール（注文送信）
    - monitoring/
      - __init__.py      # monitoring モジュール（ログ・監視）

（ルートに README.md やライセンス、セットアップファイル等を置くことを推奨します）

ツリー（テキスト表現）:

src/
└─ kabusys/
   ├─ __init__.py
   ├─ data/
   │  └─ __init__.py
   ├─ strategy/
   │  └─ __init__.py
   ├─ execution/
   │  └─ __init__.py
   └─ monitoring/
      └─ __init__.py

---

## 開発ガイド（短く）

- 各モジュールは責務を分離して実装する（例: API 呼び出しは data/execution、アルゴリズムは strategy、状態管理や可視化は monitoring）
- 単体テストを作成して戦略ロジックや注文処理の重要部分を検証する
- 実際の資金を動かす前に、バックテスト・フォワードテスト・ペーパートレードで十分に検証する
- 機密情報（APIキー等）は環境変数や安全なシークレット管理に格納する

---

## 貢献・連絡

- バグ報告や改善提案は Issue を立ててください
- プルリクエスト歓迎（実装内容にはテストとドキュメントを添えてください）

---

作成済みの雛形から実際の自動売買システムに拡張する際は、取引所／ブローカーのAPI仕様やリスク管理、法令遵守（金融商品取引法等）を必ず確認してください。