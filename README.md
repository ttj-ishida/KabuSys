# KabuSys

KabuSys は日本株の自動売買システム用の軽量な Python パッケージの骨組みです。  
本リポジトリは、データ取得・戦略・発注・監視の責務を分離したモジュール構成を提供します。現時点では基本的なパッケージ構造（API のエントリポイント）を定義しており、各モジュールに具体的な実装を追加して拡張して使います。

## 主要機能（構成）
- data — 市場データの取得／保存（履歴・板情報等）の実装場所
- strategy — 売買ロジック（シグナル生成・ポジション管理）の実装場所
- execution — 注文発行・注文管理（ブローカー／API 連携）の実装場所
- monitoring — ログ記録・メトリクス・アラート・ダッシュボード等の実装場所

各モジュールは独立して実装できるように分割されています。将来的に外部 API（例：kabuステーション等）やデータベンダーへ接続するコネクタを追加できます。

## 動作環境
- Python 3.8 以上（推奨: 3.8/3.9/3.10）
- 仮想環境（venv / conda 等）の利用を推奨

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリ URL>
   cd <リポジトリ>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows (PowerShell では .venv\Scripts\Activate.ps1)
   ```

3-1. （パッケージ化済みの場合）編集可能なインストール
   プロジェクトに `pyproject.toml` や `setup.py` がある場合：
   ```
   pip install -e .
   ```

3-2. （現状の構成）src ディレクトリを PYTHONPATH に追加して利用
   パッケージが `src/kabusys` 配下にあるため、実行時に `src` をパスに追加します。
   - 一時的に実行時のみ：
     ```
     PYTHONPATH=./src python your_script.py   # macOS / Linux
     set PYTHONPATH=.\src && python your_script.py   # Windows (cmd)
     ```
   - あるいはスクリプト内で sys.path を操作：
     ```python
     import sys
     sys.path.append("src")
     import kabusys
     ```

4. 依存ライブラリのインストール  
   現状では特別な依存はありませんが、実装する機能に応じて以下のようなパッケージが必要になる可能性があります：
   - requests / httpx（API 通信）
   - pandas / numpy（データ処理）
   - sqlalchemy（データ永続化）
   - pytest（テスト）
   必要に応じて requirements.txt を作成して `pip install -r requirements.txt` を行ってください。

## 使い方（例）

以下はシンプルな利用イメージ（モジュールは空のためダミー実装例）。実際には各モジュールにクラス・関数を実装して利用します。

例: 単純なストラテジの流れ（疑似コード）
```python
# src をパスに含めておく
import sys
sys.path.append("src")

from kabusys import data, strategy, execution, monitoring

# --- 仮のインターフェース例 ---
# dataclient = data.DataClient(api_key=...)
# strat = strategy.SimpleMovingAverageStrategy(params=...)
# executor = execution.OrderExecutor(api_credentials=...)
# monitor = monitoring.MonitoringClient()

# --- 実行ループの概念例 ---
# while trading_hours:
#     market = dataclient.fetch_latest("7203")    # 銘柄コード例
#     signal = strat.generate_signal(market)
#     if signal == "BUY":
#         executor.place_order(symbol="7203", side="BUY", size=100)
#     elif signal == "SELL":
#         executor.place_order(symbol="7203", side="SELL", size=100)
#     monitor.record(market, signal)
```

各モジュールに対して実装すべき代表的なインターフェース例：
- data
  - fetch_latest(symbol)
  - fetch_history(symbol, start, end)
  - save_tick(data)
- strategy
  - generate_signal(market_data) -> ("BUY" | "SELL" | "HOLD")
  - on_fill(order_info)
- execution
  - place_order(symbol, side, size, price=None)
  - cancel_order(order_id)
  - get_order_status(order_id)
- monitoring
  - record(metric_name, value)
  - alert(message, level="INFO")

実際の実装では、各機能をクラス化して DI（依存性注入）しやすい設計にするのが便利です。

## ディレクトリ構成
現状のファイル構成（抜粋）

- src/
  - kabusys/
    - __init__.py                # パッケージのトップレベル（バージョン・サブモジュールの公開）
    - data/
      - __init__.py
      # → market data 周りの実装用
    - strategy/
      - __init__.py
      # → 売買戦略の実装用
    - execution/
      - __init__.py
      # → 注文発行・API 連携の実装用
    - monitoring/
      - __init__.py
      # → ログ・メトリクス・アラートの実装用

ファイル一覧（現状）
- src/kabusys/__init__.py
- src/kabusys/data/__init__.py
- src/kabusys/strategy/__init__.py
- src/kabusys/execution/__init__.py
- src/kabusys/monitoring/__init__.py

## 拡張のヒント
- 各サブパッケージに対して README やドキュメント（インターフェース仕様）を追加する。
- strategy はテストしやすくするため外部依存を切り離した純粋関数／軽量クラスにする。
- execution 層は冪等性の確保、注文状態管理、リトライ・バックオフ戦略を実装する。
- monitoring ではメトリクス（Prometheus 等）やログ集約（ELK / CloudWatch）との連携を検討する。

## 貢献
改善・機能追加の PR を歓迎します。主なフロー：
1. Issue を立てて提案・議論
2. ブランチを切って実装
3. テストを追加（pytest など）
4. PR を送ってレビューを依頼

## ライセンス
プロジェクトにライセンスファイルがない場合、公開前に適切なライセンス（MIT / Apache-2.0 など）を追加してください。

---

必要であれば、各サブパッケージの具体的なインターフェース定義（型定義・抽象クラス）やサンプル実装、CI 設定（テスト・Lint）などの雛形も作成します。どの部分を優先して整備したいか教えてください。