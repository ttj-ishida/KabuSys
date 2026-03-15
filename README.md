# KabuSys — 日本株自動売買システム (README)

KabuSys は日本株の自動売買システムを想定した Python パッケージの骨組み（スケルトン）です。現在はパッケージ構造と基本情報のみが実装されており、データ取得、売買戦略、発注（実行）、監視（モニタリング）を実装するためのサブパッケージを備えています。

バージョン: 0.1.0

---

## プロジェクト概要

このプロジェクトは、日本株の自動売買アルゴリズムを構築・運用するためのモジュール構成を提供します。各責務を分離したサブパッケージにより、

- データ取得（market data）
- 売買戦略（signal/strategy）
- 注文発行・実行（execution）
- システム監視（monitoring / logging / metrics）

をそれぞれ独立して実装・テストできるように設計されています。

現時点ではインターフェースの骨組みのみで、具体的な API 呼び出しや戦略ロジックは含まれていません。実運用前にシミュレーションや単体テスト、リスク管理（資金管理・注文制限等）を必ず実装してください。

---

## 機能一覧（想定）

現バージョン（スケルトン）で想定される機能（将来実装されるもの）を記載します。

- data: 株価や板情報の取得、OHLC 時系列データの保存・前処理
- strategy: 売買シグナル生成、バックテスト用インターフェース
- execution: 注文の作成、約定管理、再送制御、API 経由の実発注機能
- monitoring: ログ出力、メトリクス収集、アラート（メール/Slack 等）

注意: 現在は各サブパッケージは空のモジュールとして存在します。必要機能は各自で実装してください。

---

## セットアップ手順

以下は開発・実行環境を整えるための一般的な手順例です。プロジェクトに `pyproject.toml` や `requirements.txt` がない場合は、必要パッケージを追加してください。

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. Python 仮想環境の作成（推奨）
   ```
   python3 -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows (PowerShell 等)
   ```

3. 開発用依存関係をインストール
   - まだ requirements.txt が無ければ、以下は一例です。実装内容に応じて追加してください。
     ```
     pip install --upgrade pip
     pip install requests pandas numpy
     pip install pytest black isort flake8    # 開発ツール
     ```
   - パッケージを編集可能モードでインストール：
     ```
     pip install -e .
     ```
     ※ setup.py / pyproject.toml が必要です。無ければ直接インタープリタから `src` をパスに追加するか、モジュールをインポートして利用してください。

4. 環境変数（API キー等）の設定（例）
   ```
   export KABU_API_KEY="your_api_key_here"
   export KABU_API_SECRET="your_api_secret"
   ```
   実際に使用する証券会社 API の仕様に従って適切に設定してください。

---

## 使い方（基本例）

現在は骨組みのため、まずはパッケージが import できることを確認します。

Python REPL で:
```python
>>> import kabusys
>>> kabusys.__version__
'0.1.0'
>>> from kabusys import data, strategy, execution, monitoring
>>> data, strategy, execution, monitoring
(<module 'kabusys.data'>, <module 'kabusys.strategy'>, <module 'kabusys.execution'>, <module 'kabusys.monitoring'>)
```

各サブパッケージに具体的なクラスや関数を実装する例（擬似コード）：

- data モジュールにマーケットデータ取得クラスを追加:
```python
# src/kabusys/data/market.py
import requests

class MarketDataClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_ohlc(self, symbol: str, period: str = "1d"):
        # TODO: 実API呼び出し実装
        raise NotImplementedError
```

- strategy モジュールに戦略クラスを追加:
```python
# src/kabusys/strategy/simple_ma.py
class SimpleMA:
    def __init__(self, short_window: int, long_window: int):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signal(self, ohlc_df):
        # TODO: シグナル生成ロジック
        return "BUY"  # または "SELL", "HOLD"
```

- execution モジュールに発注インターフェースを追加:
```python
# src/kabusys/execution/api.py
class ExecutionClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def place_order(self, symbol: str, side: str, qty: int):
        # TODO: 注文 API 呼び出し
        raise NotImplementedError
```

- monitoring モジュールにログ/監視を追加:
```python
# src/kabusys/monitoring/logging.py
import logging
logger = logging.getLogger("kabusys")
logger.setLevel(logging.INFO)
```

実装後は、これらを組み合わせてワークフロー（データ取得 → シグナル生成 → 注文発注 → 監視）を作成します。

注意: 実際の資金を用いる前に必ずペーパートレードやバックテストで動作確認を行い、注文ロジックやエラー処理、リスク制御を厳格に実装してください。

---

## ディレクトリ構成

現在のプロジェクト（提供されたソース）に基づくディレクトリ構成は以下の通りです。

- src/
  - kabusys/
    - __init__.py            # パッケージ情報 (version, __all__)
    - data/
      - __init__.py          # データ取得関連モジュールを配置
    - strategy/
      - __init__.py          # 戦略ロジックを配置
    - execution/
      - __init__.py          # 注文発行・実行ロジックを配置
    - monitoring/
      - __init__.py          # ログ・監視用モジュールを配置

推奨の追加ファイル（プロジェクト管理用）:
- pyproject.toml または setup.cfg / setup.py    # パッケージ設定
- requirements.txt                                # 依存関係
- tests/                                          # 単体テスト
- docs/                                           # ドキュメント
- examples/                                       # 利用例スクリプト
- .gitignore                                      # Git 無視設定
- README.md                                       # （このファイル）

---

## 開発時の注意点 / 推奨事項

- 実際の証券会社 API を呼ぶ場合、必ずテスト環境（ペーパートレード）で検証してください。
- エラー・例外処理、リトライ、レート制限対応を実装してください。
- 注文前に資金・建玉状況や最大注文数などをチェックするリスク管理ロジックを実装してください。
- ログ出力とメトリクス収集（Prometheus 等）を導入すると運用が容易になります。
- CI（pytest）でユニットテストと静的解析（flake8, mypy 等）を回すことを推奨します。

---

## ライセンス / コントリビューション

このリポジトリのライセンス情報は現在含まれていません。使用・配布する際は適切なライセンスを追加してください。コントリビュートする場合は、Issue / PR を送る前に開発ガイドラインやコントリビューション用のドキュメントを追加しておくとよいです。

---

必要があれば、README の補足（依存関係のテンプレート、サンプル実装、API の接続サンプル、バックテストフロー）を追加できます。どの部分を優先して充実させたいか教えてください。