# KabuSys

日本株自動売買システム（スケルトン実装）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムの骨組み（スケルトン）です。  
本リポジトリは、以下の責務を分離したモジュール構成を提供します。

- データ取得・前処理（data）
- トレーディング戦略（strategy）
- 注文実行（execution）
- 監視・ログ・メトリクス（monitoring）

現状はパッケージ構造のみが用意されており、各モジュールの具体実装はユーザが拡張して作成する想定です。自動売買のフレームワークとして、各領域を実装・差し替えしやすい形にしています。

---

## 機能一覧（予定・想定）

- 市場データ取得（リアルタイム / 過去データのフェッチ）
- データの前処理・特徴量作成
- 売買シグナル生成（複数戦略の組合せを想定）
- 注文発注・約定管理（API経由・模擬発注）
- ポジション管理・リスク管理
- 実行ログ・パフォーマンスの記録とモニタリング
- シミュレーションモードと実取引モードの切替

> 注意: 現在のコードベースはパッケージの雛形のみです。上記機能は各サブパッケージに実装してください。

---

## セットアップ手順

前提
- Python 3.8 以上（推奨）
- Git

1. リポジトリをクローンする
```bash
git clone <repository-url>
cd <repository-directory>
```

2. 仮想環境を作成して有効化（任意）
```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

3. 開発用依存パッケージをインストール
- このリポジトリには requirements.txt / pyproject.toml が含まれていないため、プロジェクトで必要なライブラリ（requests, pandas, numpy 等）を各自追加してください。例:
```bash
pip install -U pip
pip install requests pandas numpy
```

4. 編集時のインストール（開発モード）
- setup.py / pyproject.toml がある場合:
```bash
pip install -e .
```
- ない場合は、直接ソースを PYTHONPATH に通すか、上記パッケージ群をインストールして開発してください。

5. 設定ファイル（APIキー等）
- 実際の取引APIやデータプロバイダを利用する場合は、APIキーや接続情報を設定ファイル（例: `config.yaml`）や環境変数で管理してください。例:
```yaml
kabu_api:
  api_key: "YOUR_API_KEY"
  endpoint: "https://api.example.com"
mode: "simulation"  # or "live"
```

---

## 使い方（例・ガイド）

このパッケージはモジュール別に機能を実装して使うことを想定しています。以下は推奨インターフェースの一例です（実装例）。

- 例: パイプラインの簡単な流れ
```python
# sample_runner.py
from kabusys import __version__
from kabusys.data import DataLoader     # 実装を用意する
from kabusys.strategy import Strategy   # 実装を用意する
from kabusys.execution import Executor  # 実装を用意する
from kabusys.monitoring import Monitor  # 実装を用意する

print("KabuSys version:", __version__)

# 各コンポーネントは利用者が実装してください
data_loader = DataLoader(config="config.yaml")
strategy = Strategy()
executor = Executor(config="config.yaml")
monitor = Monitor()

# フローのイメージ
market_data = data_loader.fetch_latest("7203.T")       # 銘柄コードの例
signals = strategy.generate_signals(market_data)
for sig in signals:
    executor.execute(sig)
monitor.report()
```

- 各サブパッケージの想定 API（参考）
  - kabusys.data
    - DataLoader.fetch_latest(symbol, timeframe, n=100)
    - DataLoader.fetch_history(symbol, start, end)
  - kabusys.strategy
    - Strategy.generate_signals(market_data) -> list[Signal]
  - kabusys.execution
    - Executor.execute(signal) -> OrderResult
    - Executor.cancel(order_id)
  - kabusys.monitoring
    - Monitor.record(order_result)
    - Monitor.report()

上記はあくまで一例です。プロジェクトの要件に合わせてインターフェースを設計してください。

---

## ディレクトリ構成

現在の主要ファイル / ディレクトリ構成（ルートから見た例）

- src/
  - kabusys/
    - __init__.py          # パッケージメタ情報（バージョン等）
    - data/
      - __init__.py        # データ取得・前処理用モジュールを配置
    - strategy/
      - __init__.py        # 戦略関連モジュールを配置
    - execution/
      - __init__.py        # 注文実行関連モジュールを配置
    - monitoring/
      - __init__.py        # 監視・ログ用モジュールを配置

現在、各サブパッケージは初期ファイルのみ（空）です。機能を実装する場合は、それぞれのディレクトリにモジュール（例: loader.py, simple_strategy.py, broker.py, monitor.py 等）を追加してください。

---

## 開発の進め方（簡単なガイド）

- 新しい機能はサブパッケージ内にモジュールを追加して実装してください。
- 外部APIに依存するコードは抽象化（インターフェース化）して、テスト容易性を確保してください（モック可能にする）。
- 設定は環境変数・設定ファイルで切替できるようにし、シミュレーションモードを必ず用意してください（実取引の安全のため）。
- ログは構造化ログ／ファイル出力を採用し、重要なイベント（注文・約定・エラー）を記録してください。

---

## 注意事項

- 実際の資金を使って取引を行う前に、必ずシミュレーションで十分な検証を行ってください。
- 金融関連の実装（注文ロジック、リスク管理、API利用）には法規制や取引所／ブローカーのルールが関わります。利用前に必ず確認してください。
- このリポジトリは雛形です。運用前の保証や責任は負いません。

---

ご不明点や README の追加要望（例: 設計方針、サンプル戦略実装、CI 設定の追加等）があれば教えてください。README をプロジェクトの進行に合わせて拡張します。