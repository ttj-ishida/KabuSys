KabuSys
=======

日本株自動売買システム（骨組み）

バージョン: 0.1.0

概要
----
KabuSys は日本株の自動売買システムのための軽量なパッケージ構成（スケルトン）です。  
このリポジトリは、データ取得、ストラテジーロジック、売買実行、監視の4つの責務を分離した構造を提供します。まだ具体的な実装は含まれておらず、拡張して利用するためのテンプレート／出発点として設計されています。

主な意図
- 開発者が自動売買機能を責務ごとに実装して組み合わせられるようにする
- テストやCI、デプロイを考慮したシンプルなパッケージレイアウトを提供する

機能一覧（想定／拡張ポイント）
-----------------
- data: 市場データの取得・保存・履歴管理（板情報、約定、時系列データなど）
- strategy: 売買戦略の実装（シグナル生成、ポジション管理、パラメータ管理）
- execution: 注文発行・約定管理（kabuステーション／証券APIとの連携を想定）
- monitoring: ログ、アラート、運用状況の可視化（稼働監視、パフォーマンス集計）

セットアップ手順
---------------
前提
- Python 3.8 以上を推奨

1. リポジトリをクローン
   git clone <リポジトリURL>
   cd <リポジトリディレクトリ>

2. 仮想環境を作成・有効化（任意だが推奨）
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate

3. 依存パッケージのインストール
   現状 requirements.txt や pyproject.toml に依存情報は含まれていません。  
   実装に合わせて必要なライブラリ（requests、pandas、websocket-client 等）をインストールしてください。
   例:
   pip install requests pandas

4. パッケージを使えるようにする
   開発中は PYTHONPATH を通す方法が手軽です（プロジェクトルートで実行）。
   # macOS / Linux
   export PYTHONPATH=$(pwd)/src
   # Windows (PowerShell)
   $env:PYTHONPATH = "$(Resolve-Path .\src)"

   あるいは、将来的に pyproject.toml や setup.py を追加して、
   pip install -e . で編集可能なインストールを行えます。

使い方（例）
-----------
パッケージはまだ具体的な実装を持たないため、まずはサブパッケージをインポートして拡張してください。

簡単な確認例:
```
from kabusys import __version__
import kabusys
import kabusys.data as data
import kabusys.strategy as strategy
import kabusys.execution as execution
import kabusys.monitoring as monitoring

print("KabuSys version:", __version__)
print("Available subpackages:", kabusys.__all__)
```

拡張（スケルトン例）
- data にデータ取得クラスを実装する例:
```
# src/kabusys/data/client.py
class DataClient:
    def fetch_candles(self, symbol, timeframe):
        raise NotImplementedError
```

- strategy に戦略ベースを作る例:
```
# src/kabusys/strategy/base.py
class StrategyBase:
    def on_tick(self, tick):
        """ティック受信時の処理。注文は execution 経由で発行する"""
        raise NotImplementedError
```

- execution に実行クライアントを作る例:
```
# src/kabusys/execution/client.py
class ExecutionClient:
    def send_order(self, order):
        raise NotImplementedError
```

- monitoring にログやアラート機能を実装:
```
# src/kabusys/monitoring/logger.py
def log_event(event):
    pass
```

開発フローの例
- data.Client を実装してローカルまたはAPIからデータを取得
- strategy.Strategy を作り、DataClient からデータを受けてシグナルを生成
- execution.Client が証券APIへ注文を送信
- monitoring で稼働状況や注文履歴を集約・可視化

ディレクトリ構成
---------------
現状のファイル構成（主要部）
```
src/
  kabusys/
    __init__.py            # パッケージメタ情報 (version, __all__)
    data/
      __init__.py
      # (ここにデータ取得関連のモジュールを追加)
    strategy/
      __init__.py
      # (戦略ロジックを追加)
    execution/
      __init__.py
      # (注文実行クライアントを追加)
    monitoring/
      __init__.py
      # (監視・ログ関連を追加)
```

開発・貢献
--------
- Issue / Pull Request を歓迎します。拡張を行う際はモジュールごとに責務を分け、テストを追加してください。
- 具体的実装（APIキーの管理、発注ロジック、レート制限対策等）は慎重に行ってください。実トレードに用いる場合は十分にバックテスト・リスク管理を行ってください。

ライセンス
---------
このリポジトリにはライセンスファイルが含まれていません。利用・配布を行う前にライセンスを明示してください（例: MIT、Apache-2.0 など）。

補足
---
このリポジトリは骨組み（テンプレート）です。実際の自動売買システムを作成する際は、金融規制・証券会社の利用規約・API仕様・セキュリティ（秘密情報の保護）を確認・遵守してください。