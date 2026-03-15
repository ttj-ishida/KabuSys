# KabuSys

日本株自動売買システムのための軽量フレームワーク（プロジェクト初期版）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援するためのシンプルなフレームワーク骨格です。モジュールは以下の責務に分かれており、ユーザーは各モジュールを実装・拡張して自動売買ロジックを組み立てます。

- data: 市場データの取得・加工
- strategy: 売買戦略のロジック
- execution: 注文実行や取引APIとの接続
- monitoring: ログ、アラート、ダッシュボード等の監視機能

このリポジトリは現時点では骨組み（パッケージ構造）のみ実装しており、実際のデータソースや証券会社APIへの接続・具体的な戦略実装はユーザーが追加します。

---

## 機能一覧

現状（v0.1.0）は以下を提供します。

- パッケージ化されたモジュール構成（data / strategy / execution / monitoring）
- パッケージのバージョン情報（kabusys.__version__）
- 拡張しやすいディレクトリ構成とインターフェースを想定した雛形

将来的に想定している機能（実装が必要）:

- 株価データの取得（Kabuステーション、証券API、CSV読み込み等）
- バックテスト環境
- 注文の発行／約定管理（成行、指値、注文取消し 等）
- リスク管理（ポジション管理、損切りルール等）
- 監視と通知（メール、Slack、ログ保存、メトリクス）

---

## セットアップ手順

推奨環境
- Python 3.8 以上

リポジトリをクローンしてローカルで使う手順（パッケージ化ファイルが無い場合の簡易利用方法）:

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <this-repo>
   ```

2. 仮想環境を作成・有効化
   - Windows
     ```
     python -m venv venv
     venv\Scripts\activate
     ```
   - macOS / Linux
     ```
     python3 -m venv venv
     source venv/bin/activate
     ```

3. 依存パッケージをインストール
   - 現状 `requirements.txt` がない場合は、必要なライブラリ（requests、pandas 等）を手動でインストールしてください。
     ```
     pip install requests pandas
     ```
   - 将来的に `pyproject.toml` / `setup.cfg` があれば:
     ```
     pip install -e .
     ```

4. 開発時にソースを直接参照するには、プロジェクトのルートを PYTHONPATH に含めるか、IDE のソースパスに追加してください。
   - 例（Linux/macOS）
     ```
     export PYTHONPATH="${PWD}/src:$PYTHONPATH"
     ```

---

## 使い方（基本例）

パッケージのインポートとバージョン確認:
```python
import kabusys
print(kabusys.__version__)  # "0.1.0"
```

基本的な拡張の例（雛形）

- strategy モジュールに戦略クラスを実装
- data モジュールでデータ取得関数を実装
- execution モジュールで注文発行を実装
- monitoring モジュールでログやアラートを実装

例（簡易的な擬似コード）:
```python
# my_strategy.py
from kabusys import data, strategy, execution, monitoring

class MyStrategy:
    def __init__(self):
        # 初期化（パラメータ等）
        pass

    def on_market_data(self, market_snapshot):
        # market_snapshot を受け取り売買判断を行う
        # 例: シンプルな移動平均クロス等（ここはユーザ実装）
        if should_buy(market_snapshot):
            return {"side": "BUY", "symbol": "7203.T", "qty": 100}
        return None

# 実行ループ（最小構成）
def main():
    strat = MyStrategy()
    exec_client = execution.YourExecutionClient()   # 実装が必要
    monitor = monitoring.YourMonitor()             # 実装が必要

    while True:
        # データ取得（ユーザ実装）
        market_snapshot = data.get_latest_snapshot("7203.T")
        order = strat.on_market_data(market_snapshot)
        if order:
            result = exec_client.send_order(order)
            monitor.record_trade(result)
```

上のコードはあくまで構成例です。実際の実装ではエラーハンドリング・再接続・約定確認・注文キャンセル・レート制限対応等が必要です。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・フォルダ構成（現状）

- src/
  - kabusys/
    - __init__.py            # パッケージ定義（バージョン、エクスポート）
    - data/
      - __init__.py          # データ取得関連モジュールを追加
    - strategy/
      - __init__.py          # 戦略ロジック関連を追加
    - execution/
      - __init__.py          # 注文実行・APIクライアントを追加
    - monitoring/
      - __init__.py          # 監視・ログ関連を追加

（将来的に以下を追加する想定）
- tests/                    # ユニットテスト
- examples/                 # 利用例スクリプト
- requirements.txt          # 依存ライブラリ
- pyproject.toml / setup.cfg # パッケージインストール用

---

## 開発・拡張の指針

- 各モジュールは疎結合にして、外部API依存部（例: 証券会社API）はインターフェース化して差し替え可能にしてください。
- 実マーケットでの利用時は入念なバックテストとペーパー取引（シミュレーション）で安全性を確認してください。
- 資金管理、例外処理、ログ / トレーシングを必ず実装してください。
- API キー / 認証情報はソース管理に含めず、環境変数や安全なシークレット管理を使用してください。

---

## ライセンスと貢献

現時点ではライセンスファイルは含まれていません。商用利用や公開時は適切なライセンスを追加してください。貢献（機能追加、バグ修正等）はプルリクエストで受け付けます。まずは Issue を立てて設計方針を共有してください。

---

補足:
このリポジトリはベース骨格（テンプレート）です。実運用を行う前に、取引所/証券会社のAPI仕様、法的要件、リスク管理を十分に確認・実装してください。