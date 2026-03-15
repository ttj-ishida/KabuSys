# KabuSys

KabuSys は日本株向けの自動売買システムのための軽量なフレームワーク（骨組み）です。  
このリポジトリはプロジェクトの基本構造を提供し、データ取得、ストラテジ、注文実行、監視機能をそれぞれ独立したサブパッケージとして整理しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のコンポーネントに分かれます（各コンポーネントは現在ベースとなるパッケージとして用意されています）:

- data: 市場データの取得・前処理を担当
- strategy: 売買判断ロジック（ストラテジ）を実装
- execution: 注文発行（ブローカー API 連携など）を担当
- monitoring: ログ記録、通知、稼働監視などを担当

このリポジトリはスタートポイント（スケルトン）であり、各機能はプロジェクトの要件に合わせて実装・拡張して使います。

---

## 機能一覧

現在のコードベースはフレームワーク（パッケージ構成）を提供します。将来的に実装する想定の主要機能は以下です。

- 市場データ取得（リアルタイム・過去データ）
- データの前処理（欠損値処理、リサンプリング、指標計算）
- 複数ストラテジの管理と評価
- 注文発行（成行/指値/逆指値など）と約定管理
- 監視・通知（ログ保存、メール/Slack 通知、稼働監視）
- バックテスト基盤（将来的に追加可能）

---

## セットアップ手順

前提: Python 3.8 以上を推奨します（プロジェクトの要件に合わせて調整してください）。

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境の作成（推奨）
   - venv を使用する場合:
     ```
     python -m venv .venv
     source .venv/bin/activate   # macOS / Linux
     .venv\Scripts\activate      # Windows
     ```

3. 開発環境にインストール（editable）
   ```
   pip install --upgrade pip
   pip install -e .
   ```
   ※ requirements.txt がある場合は `pip install -r requirements.txt` を実行してください。

4. 動作確認（簡単なインポート確認）
   ```python
   >>> import kabusys
   >>> print(kabusys.__version__)
   0.1.0
   ```

---

## 使い方

このリポジトリはベースとなるパッケージのみ含んでいるため、まずは各サブパッケージに実装を追加して使います。以下は実装例（テンプレート）と利用例です。

- データ取得モジュール（例: src/kabusys/data/csv_feed.py）
  ```python
  # src/kabusys/data/csv_feed.py
  from typing import Iterator
  import pandas as pd

  class CSVDataFeed:
      def __init__(self, path: str):
          self.df = pd.read_csv(path)

      def iter_bars(self) -> Iterator[dict]:
          for _, row in self.df.iterrows():
              yield row.to_dict()
  ```

- ストラテジ（例: src/kabusys/strategy/simple_momentum.py）
  ```python
  class SimpleMomentum:
      def __init__(self, window: int = 5):
          self.window = window
          self.prices = []

      def on_bar(self, bar):
          self.prices.append(bar['close'])
          if len(self.prices) > self.window:
              self.prices.pop(0)
          # シグナル生成はここで行う
          return None  # 例: 'BUY' / 'SELL' / None
  ```

- 実行エンジン（例: src/kabusys/execution/broker_stub.py）
  ```python
  class ExecutionEngine:
      def send_order(self, symbol: str, side: str, qty: int, price: float = None):
          # 実際のブローカー API をここで呼ぶ
          print(f"Order -> {side} {symbol} {qty} @ {price}")
  ```

- 監視（例: src/kabusys/monitoring/logger.py）
  ```python
  import logging
  logger = logging.getLogger('kabusys')
  ```

- 簡単な実行例
  ```python
  from kabusys.data.csv_feed import CSVDataFeed
  from kabusys.strategy.simple_momentum import SimpleMomentum
  from kabusys.execution.broker_stub import ExecutionEngine

  data = CSVDataFeed('sample.csv')
  strat = SimpleMomentum(window=5)
  exec_engine = ExecutionEngine()

  for bar in data.iter_bars():
      signal = strat.on_bar(bar)
      if signal == 'BUY':
          exec_engine.send_order(symbol='7203.T', side='BUY', qty=100)
      elif signal == 'SELL':
          exec_engine.send_order(symbol='7203.T', side='SELL', qty=100)
  ```

上記はあくまでテンプレートです。実運用ではエラーハンドリング、再試行、注文確認、ログ保存、認証管理（APIキーの安全な管理）など、多くの追加実装が必要です。

---

## ディレクトリ構成

プロジェクトの主要なファイル構成は以下の通りです。

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py           # パッケージ定義、__version__ 等
│     ├─ data/
│     │  └─ __init__.py        # データ取得関連モジュールを配置
│     ├─ strategy/
│     │  └─ __init__.py        # ストラテジ関連モジュールを配置
│     ├─ execution/
│     │  └─ __init__.py        # 注文実行関連モジュールを配置
│     └─ monitoring/
│        └─ __init__.py        # 監視・ログ関連モジュールを配置
├─ README.md
├─ setup.py / pyproject.toml   # （任意）パッケージ設定
└─ (その他、テストや設定ファイル)
```

---

## 開発・拡張のヒント

- 各サブパッケージ（data, strategy, execution, monitoring）にインターフェース（抽象クラス）を定義すると、モジュール間の結合度が下がりテストがしやすくなります。
- 実運用ではブローカー API の呼び出しは非同期化（並列実行）やキューイングを検討してください。
- API キーや機密情報は環境変数やシークレット管理ツールで管理してください。
- ロギングは構造化ログ（JSON など）にすると監視や解析が容易です。

---

必要であれば、README に以下を追記できます:
- 具体的な API 連携の実装例（例: kabuステーション/kabusapi）
- バックテスト用のサンプルデータと実行コマンド
- CI / CD、テストの実行方法

追加の要望があれば、目的（例: 実際の kabu API と接続したい、バックテスト機能を加えたい）を教えてください。README をそれに合わせて拡張します。