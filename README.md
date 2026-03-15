# KabuSys

KabuSys は日本株向けの自動売買システムのための軽量フレームワーク（骨組み）です。データ取得、売買戦略（ストラテジー）、注文実行、監視（モニタリング）を役割ごとに分離したパッケージ構成を提供し、ユーザーは各モジュールを実装・拡張して自動売買ロジックを作成できます。

バージョン: 0.1.0

---

## プロジェクト概要

このリポジトリはプロジェクトの骨組み（スキャフォールド）を提供します。以下のサブパッケージが含まれており、それぞれの役割を分離しています。

- kabusys.data: 価格データや板情報などの取得・整形を担当
- kabusys.strategy: 売買判断ロジック（戦略）を実装する場所
- kabusys.execution: 証券会社APIなどを呼び出して実際に注文を出す部分
- kabusys.monitoring: ログ・メトリクス・アラートなどの監視機能

現時点では各モジュールはパッケージの骨組みのみ（空の __init__.py）ですが、拡張して自動売買システムを構築できます。

---

## 機能一覧（想定・拡張ポイント）

このベースで実装・拡張する想定の機能例:

- データ取得（リアルタイムティック、板情報、約定履歴、過去データ）
- 戦略表現（シグナル生成、ポジション管理、リスク管理）
- 注文実行（注文送信、注文キャンセル、約定確認）
- 監視（ログ、メトリクス収集、アラート、Webダッシュボード）
- プラグイン方式での戦略・データソース・実行バックエンドの差し替え

---

## セットアップ手順

1. 必要環境
   - Python 3.8 以上（3.9/3.10/3.11 推奨）
   - 仮想環境の利用を推奨（venv, virtualenv, conda 等）

2. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリディレクトリ>
   ```

3. 仮想環境作成と有効化（例: venv）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

4. インストール（開発・編集しながら使う場合）
   ```
   pip install -e .
   ```
   ※ このプロジェクトに setup.py / pyproject.toml があることを想定しています。無い場合は、直接 `PYTHONPATH` に src を追加して利用できます:
   ```
   export PYTHONPATH=$(pwd)/src:$PYTHONPATH
   ```

5. 依存パッケージがある場合は requirements.txt を参照してインストールしてください（現時点では特定の依存は含まれていません）。

6. (任意) 証券会社APIキーや接続情報の設定
   - 環境変数や設定ファイル（例: .env, config.yaml）で管理することを推奨します。
   - 例:
     ```
     export KABU_API_KEY=xxxxxxxx
     export KABU_API_SECRET=yyyyyyyy
     ```

---

## 使い方（基本例・拡張ガイド）

現状は骨組みパッケージのため、まずは簡単な動作確認と拡張の例を示します。

- パッケージ読み込みとバージョン確認:
```python
import kabusys
print(kabusys.__version__)  # => "0.1.0"
```

- モジュール参照例:
```python
import kabusys.data
import kabusys.strategy
import kabusys.execution
import kabusys.monitoring
```

- 戦略・実行インターフェースのスケルトン（例）
  - 以下は README 内で推奨する拡張例のスケルトンです。実際には自分のプロジェクトに合わせてメソッドや引数を設計してください。

```python
# src/kabusys/strategy/simple_strategy.py
class SimpleStrategy:
    def __init__(self, config):
        self.config = config

    def on_market_data(self, market_data):
        """
        市場データを受け取ってシグナルを返す。
        例: {'signal': 'BUY', 'symbol': '7203', 'size': 100}
        """
        # ここにロジックを実装
        return None
```

```python
# src/kabusys/execution/kabu_connector.py
class KabuConnector:
    def __init__(self, api_key, api_secret):
        # 初期化（認証など）
        pass

    def send_order(self, symbol, side, size, price=None):
        """
        注文を送信する。
        """
        # ここで実際のAPI呼び出しを行う
        return {'order_id': 'xxx', 'status': 'accepted'}
```

- 実行フローの例（擬似コード）:
```python
strategy = SimpleStrategy(config)
connector = KabuConnector(api_key, api_secret)

while True:
    market_data = ...  # kabusys.data から取得
    signal = strategy.on_market_data(market_data)
    if signal:
        connector.send_order(signal['symbol'], signal['signal'], signal['size'])
```

---

## ディレクトリ構成

現状のファイル構成（簡略化）:

```
<project-root>/
├─ src/
│  └─ kabusys/
│     ├─ __init__.py                 # パッケージメタデータ（バージョン等）
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
├─ README.md
└─ (その他: setup.py / pyproject.toml / requirements.txt など)
```

推奨追加ファイル（開発時）:
- docs/ : 詳細ドキュメント
- examples/ : サンプル戦略・実行スクリプト
- tests/ : 単体テスト
- config/ : 設定テンプレート

---

## 開発者向けメモ

- 各サブパッケージに共通のインターフェース（抽象クラス）を定義しておくと互換性が保ちやすくなります（例: StrategyBase, ExecutionBackendBase）。
- テストはシミュレーション用のモックAPIを用意して行うことを推奨します（実環境の注文はリスクがあるため）。
- 監視はログ出力（構造化ログ）＋メトリクス（Prometheus等）＋アラート（メール/Slack）を組み合わせると安心です。

---

## 貢献・ライセンス

- 貢献歓迎します。Issue/PR を通じてご提案ください。
- ライセンスはプロジェクトルートに LICENSE ファイルを配置してください（ここでは指定していません）。

---

この README は骨組みパッケージに基づく説明です。実際の取引を行う前に、必ず十分な検証（バックテスト・ペーパートレード）を行い、リスク管理を徹底してください。