# KabuSys

KabuSys は日本株の自動売買システムのベースとなる Python パッケージの骨組みです。  
このリポジトリはプロジェクト構成（data, strategy, execution, monitoring）を提供し、実際のデータ取得・売買ロジック・注文送信・監視機能を実装して拡張するための出発点になります。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントを持つモジュール構成になっています。

- data: 市場データの取得／前処理
- strategy: 売買戦略（シグナル生成）
- execution: 注文の作成と発注（実取引／モック）
- monitoring: ログ、メトリクス、アラートなどの監視機能

現在のコードベースは骨組み（パッケージ初期化ファイルのみ）を提供しており、各モジュールに具象実装を追加して運用することを想定しています。

---

## 機能一覧（想定・拡張ポイント）

- 市場データ取得（例: REST / WebSocket / CSV ロード）
- データの前処理（指標計算、スムージング、欠損処理）
- 売買シグナル生成（移動平均、RSI、機械学習ベースなど）
- 注文管理（発注、取消、注文状態追跡）
- 取引ログとモニタリング（履歴保存、通知、ダッシュボード連携）
- テスト用のモック実装（シミュレーション / バックテスト用）

注: 上記は現状の骨組みに対する推奨機能で、各機能はユーザが実装します。

---

## セットアップ手順

このリポジトリは Python のパッケージ構成（src 配下）を持っています。以下は開発環境の一般的なセットアップ手順です。

必要条件:
- Python 3.8 以上（推奨: 3.9+）
- pip, virtualenv（または venv）

1. リポジトリをクローン
```
git clone <repository-url>
cd <repository-directory>
```

2. 仮想環境の作成と有効化（例: venv）
```
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

3. 開発用依存のインストール  
（requirements.txt や pyproject.toml が無ければ、必要なパッケージを手動で追加します。例: requests, pandas など）
```
pip install -U pip setuptools
# 例: データ処理に pandas を使う場合
pip install pandas requests
```

4. （任意）パッケージを開発モードでインストール
プロジェクトに setup.py または pyproject.toml があれば：
```
pip install -e .
```
無ければ、ローカルの src ディレクトリを PYTHONPATH に追加するか、直接モジュールを import してください。

---

## 使い方（基本例）

現状は各サブパッケージが空のパッケージ（初期化のみ）です。まずは簡単な動作確認としてバージョン取得を行えます。

Python REPL やスクリプトで:
```python
import kabusys
print(kabusys.__version__)  # "0.1.0"
```

各モジュールに具体的な関数やクラスを追加した場合のサンプルワークフロー例（擬似コード）:
```python
from kabusys.data import MarketDataClient
from kabusys.strategy import MovingAverageStrategy
from kabusys.execution import OrderExecutor
from kabusys.monitoring import Monitor

# データ取得
md = MarketDataClient(api_key="...", endpoint="...")
df = md.fetch_history(symbol="7203.T", period="1d", length=200)

# 戦略でシグナル生成
strategy = MovingAverageStrategy(short_window=20, long_window=50)
signals = strategy.generate_signals(df)

# 注文実行
executor = OrderExecutor(account_id="...", api_token="...")
for signal in signals:
    if signal.action == "BUY":
        executor.place_order(symbol=signal.symbol, side="BUY", size=signal.size)
    elif signal.action == "SELL":
        executor.place_order(symbol=signal.symbol, side="SELL", size=signal.size)

# モニタリング
monitor = Monitor()
monitor.log_trade(...)
monitor.send_alert_if_needed(...)
```

README 上の擬似 API は実装の一例です。実際には各クラスや関数をプロジェクト要件に合わせて設計・実装してください。

---

## 拡張ガイド（実装のヒント）

- data パッケージ:
  - 外部 API（証券会社 API、価格データ提供サービス）との認証・取得処理を実装
  - pandas DataFrame を返すインターフェースを推奨

- strategy パッケージ:
  - 単一責任のクラス設計（データインジェスト -> シグナル生成 -> ポジション管理）
  - ユニットテストしやすい純粋関数・小さなクラスを心がける

- execution パッケージ:
  - 実取引用のラッパーと、モック/バックテスト用のエミュレータを分離
  - 注文のリトライや例外処理、状態追跡の実装

- monitoring パッケージ:
  - ログ（構造化ログ）やメトリクス、アラート（メール/Slack）を統一的に扱う

---

## ディレクトリ構成

現在のリポジトリ構成（抜粋）:
```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py          # パッケージメタ情報（バージョンなど）
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
└─ README.md
```

各サブパッケージには今後、モジュールファイル（例: client.py, strategy.py, executor.py, monitor.py など）を追加していきます。

---

## 開発者向けメモ

- テスト: pytest などを導入してユニットテスト・統合テストを整備してください。
- CI: GitHub Actions 等で lint（flake8 / black）やテストを自動化するのを推奨します。
- セキュリティ: API キー等の機密情報は環境変数やシークレットマネージャで管理し、リポジトリに直接含めないでください。
- ライセンス: プロジェクトに適切なライセンスファイルを追加してください（例: MIT, Apache-2.0）。

---

## 参考例（開始用テンプレート）

data/__init__.py に簡易クライアントを追加する例:
```python
# src/kabusys/data/client.py
import pandas as pd

class MarketDataClient:
    def fetch_history(self, symbol: str, period: str, length: int) -> pd.DataFrame:
        # TODO: 実装 (外部API呼び出し、CSV 読み込み等)
        raise NotImplementedError
```

同様に、strategy, execution, monitoring にインターフェースを定義して実装を追加してください。

---

必要であれば、README に含める具体的な API サンプルやテンプレート実装（各パッケージ用のスターターコード）を作成します。どの機能から実装したいか教えてください。