# KabuSys

KabuSys は日本株向けの自動売買システムの骨組み（スケルトン）です。現時点ではパッケージ構成のみが定義されており、データ取得、戦略、約定（実行）、監視の各コンポーネントを実装して拡張できるようになっています。

バージョン: 0.1.0

---

## プロジェクト概要

このプロジェクトは、日本株自動売買システムの基盤ライブラリです。以下の責務に分かれたモジュール構成を提供します。

- data: 市場データやヒストリカルデータの取得・整形を担う
- strategy: 売買戦略（シグナル生成）を実装する場所
- execution: 注文発行・約定処理を行う（ブローカーAPIラッパー等）
- monitoring: ログ、メトリクス、アラート、状態監視等

現状（初期段階）はモジュールの雛形のみが用意されています。実際の売買ロジックや接続はユーザーが実装して拡張してください。

---

## 機能一覧

現状の提供機能（骨組み）

- パッケージ化されたモジュール構成（data, strategy, execution, monitoring）
- バージョン情報（kabusys.__version__）
- 拡張しやすいプロジェクトレイアウト

将来的に想定している機能（参考）

- リアルタイム／歴史データの取得インターフェース
- 戦略プラグイン（バックテスト・フォワードテスト対応）
- ブローカーAPI（kabu.com など）を使った注文執行モジュール
- ログ・ダッシュボード・アラート等の監視機能

---

## セットアップ手順

動作環境の例

- Python 3.8 以上を推奨

リポジトリをローカルで使う基本的な手順（パッケージ化が未作成の場合）

1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <リポジトリ>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - (Unix/macOS) source .venv/bin/activate
   - (Windows) .venv\Scripts\activate

3. 依存パッケージがあればインストール
   - pip install -r requirements.txt
   （requirements.txt が無ければ空）

4. 開発時のパス設定（2つの方法）
   - 方法A: PYTHONPATH を設定して実行
     - (Unix/macOS) export PYTHONPATH=$(pwd)/src
     - (Windows PowerShell) $env:PYTHONPATH = "$(Get-Location)\src"
     - その後 Python スクリプトから import kabusys が可能
   - 方法B: パッケージ化して editable インストール
     - pyproject.toml または setup.py を用意した上で:
       - pip install -e .

備考: 現在のリポジトリに pyproject.toml / setup.py が無い場合は方法Aが確実です。

---

## 使い方

基本的なインポート例：

```python
# src を PYTHONPATH に追加している前提
import kabusys

print(kabusys.__version__)  # "0.1.0"

# 各サブモジュールは拡張して実装します
import kabusys.data as data
import kabusys.strategy as strategy
import kabusys.execution as execution
import kabusys.monitoring as monitoring
```

各モジュールに期待する役割（実装例の指針）：

- data
  - クラス例: MarketDataProvider, HistoricalDataLoader
  - 役割: OHLCVや板情報を取得・整形して戦略に渡す
- strategy
  - クラス例: StrategyBase（抽象クラス）、MyStrategy（実装）
  - メソッド例: on_bar(bar), on_tick(tick), generate_signals()
- execution
  - クラス例: ExecutionClient（ブローカAPIラッパー）
  - メソッド例: send_order(order), cancel_order(order_id), get_positions()
- monitoring
  - クラス例: Monitor, Logger, MetricsExporter
  - 役割: ログ出力、取引履歴の収集、アラート送信

簡単な戦略の擬似スケルトン：

```python
# src/kabusys/strategy/my_strategy.py
from kabusys.strategy import StrategyBase  # 仮の抽象クラス

class MyStrategy(StrategyBase):
    def on_bar(self, bar):
        # bar: { 'symbol': '7203.T', 'open': ..., 'close': ... }
        # シグナル生成ロジックをここに実装
        if self.should_buy(bar):
            return {'action': 'buy', 'symbol': bar['symbol'], 'qty': 100}
        return None
```

実行（注文）フロー例：

1. data から最新データを取得
2. strategy にデータを渡してシグナルを得る
3. execution にシグナルを渡して注文を発行
4. monitoring で結果やメトリクスを記録・監視

---

## ディレクトリ構成

プロジェクトの主要ファイルとフォルダ（現状のスケルトン）

- src/
  - kabusys/
    - __init__.py         # パッケージ定義（__version__ = "0.1.0"）
    - data/
      - __init__.py       # データ取得関連モジュール（空）
    - strategy/
      - __init__.py       # 戦略関連モジュール（空）
    - execution/
      - __init__.py       # 約定（実行）関連モジュール（空）
    - monitoring/
      - __init__.py       # 監視関連モジュール（空）
- README.md              # （このファイル）
- （その他: requirements.txt, pyproject.toml, tests/ などは追加可能）

ファイル例（現在の内容）
- src/kabusys/__init__.py
  - docstring: "KabuSys - 日本株自動売買システム"
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]

---

## 拡張・実装のガイドライン（簡易）

- 戦略は副作用をできるだけ持たない（注文発行は execution に委譲）
- execution はブローカーAPIに依存するため、抽象化インターフェースを作り外部サービス差し替えを容易にする
- data はストリーミング（リアルタイム）とバッチ（バックテスト）で API を分けると保守性が高まる
- monitoring はログの整形・蓄積・可視化（Prometheus / Grafana 等）を想定する

---

## 貢献・ライセンス

- このリポジトリは骨組みです。Issue / Pull Request での拡張提案や実装歓迎します。
- ライセンスはリポジトリに明記してください（現状は未指定）。

---

必要であれば、README に以下を追加できます：
- pyproject.toml / setup.cfg のサンプル（pip install -e . で開発インストール可能にする）
- サンプル戦略・バックテスト実装のテンプレート
- CI / テストの設定例（pytest, GitHub Actions）
要望があれば追加で作成します。