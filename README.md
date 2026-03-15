# KabuSys

日本株自動売買システムのための軽量ライブラリ骨組みです。  
このリポジトリは、データ取得（data）、売買戦略（strategy）、注文実行（execution）、および監視（monitoring）という責務ごとに整理されたパッケージ構成を提供します。実際の取引ロジックや外部API接続は各サブパッケージに実装して拡張する想定です。

バージョン: 0.1.0

---

## 機能一覧

- プロジェクト構成のテンプレート（src 配下のパッケージ構造）
- 役割別サブパッケージ
  - data: 市場データの取得・整形
  - strategy: 売買戦略の実装
  - execution: 注文送信・約定処理
  - monitoring: ログ、メトリクス、アラート
- 軽量かつ拡張しやすい骨組み（各モジュールは自由に実装可能）

---

## 前提条件

- Python 3.8+
- 仮想環境の利用を推奨
- 外部API（証券会社API 等）を利用する場合は、別途 API キーやクレデンシャルが必要

---

## セットアップ手順

以下はローカルで開発／利用する一般的な手順例です。

1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージのインストール  
   - このリポジトリには requirements ファイルが含まれていないため、プロジェクト固有の依存は適宜追加してください。  
   - 開発中は次のいずれかの方法でソースをパスに追加して利用できます。

   方法 A: 開発モードでインストール（プロジェクトに pyproject.toml または setup.py がある場合）
   ```bash
   pip install -e .
   ```

   方法 B: PYTHONPATH を通す（簡易）
   ```bash
   export PYTHONPATH=$(pwd)/src:$PYTHONPATH  # macOS / Linux
   set PYTHONPATH=%cd%\src;%PYTHONPATH%     # Windows (PowerShell では異なる)
   ```

4. （任意）テスト／リンターのセットアップ  
   - pytest、flake8 などを導入してテストや静的解析を行ってください。

---

## 使い方

基本的な利用例と拡張ガイドを示します。現状のパッケージは骨組みのため、具体的な機能は各自で実装してください。

- パッケージの読み込みとバージョン確認
```python
import kabusys

print(kabusys.__version__)  # "0.1.0"
```

- サブパッケージのインポート（実装を追加して利用）
```python
from kabusys import data, strategy, execution, monitoring

# それぞれのパッケージに実装を追加して使用します
```

- 戦略（strategy）の拡張（例: 単純な売買決定関数）
  - strategy パッケージ内にクラスや関数を実装して、データ入力を受けて売買判断を返すようにします。

```python
# src/kabusys/strategy/simple.py (例)
class SimpleStrategy:
    def decide(self, market_data):
        # market_data を解析して "buy" / "sell" / "hold" を返す
        return "hold"
```

- 実行（execution）の実装例
  - execution パッケージ内で実際の注文送信ロジックを実装します。外部証券会社 API がある場合はそのクライアントを組み込みます。

```python
# src/kabusys/execution/client.py (例)
class ExecutionClient:
    def send_order(self, symbol, side, quantity):
        # 外部APIに注文を送信する処理を実装
        pass
```

- 監視（monitoring）の利用例
  - ログ出力やメトリクス、アラート送信などを実装します。簡易的には logging を利用します。

```python
import logging
logger = logging.getLogger("kabusys")
logger.info("strategy started")
```

注意: 上記はあくまで実装例です。実際の取引を行う場合は、健全なエラーハンドリング、注文の冪等性、リスク管理、接続の再試行、テスト環境（ペーパー取引）での検証などを必ず行ってください。

---

## 推奨される拡張方針

- data:
  - 市場データの取得、時系列の整形、インジケーター計算などをまとめる
  - キャッシュ・差分更新などで効率化

- strategy:
  - 戦略ごとにクラス化し、共通インタフェース（例: initialize、on_tick、on_bar、finalize）を定義する
  - 単体テストを用意して戦略の期待挙動を自動検証する

- execution:
  - 注文の送信・キャンセル・注文状態の照会を分離して実装する
  - 実取引とテスト（ペーパー）を切り替えられる抽象化を行う

- monitoring:
  - ログ、メトリクス収集（Prometheus など）、アラート（Slack、メール）を実装する

---

## ディレクトリ構成

現在の最小構成は以下の通りです。

```
.
├── src/
│   └── kabusys/
│       ├── __init__.py           # パッケージ初期化（バージョン等）
│       ├── data/
│       │   └── __init__.py       # データ取得・整形用モジュールを配置
│       ├── strategy/
│       │   └── __init__.py       # 売買戦略を配置
│       ├── execution/
│       │   └── __init__.py       # 注文実行ロジックを配置
│       └── monitoring/
│           └── __init__.py       # 監視・ロギングを配置
```

実装を追加する際は、各サブパッケージ内にさらにモジュールやサブパッケージを作成してください。

---

## 貢献・ライセンス

- 貢献: プルリクエスト歓迎します。機能追加やバグ修正は issue を立てていただくとスムーズです。
- ライセンス: このリポジトリにライセンスファイルがある場合はそれに従ってください。明記されていない場合は運用ルールをプロジェクト内で決めてください。

---

以上がこのコードベースのREADMEです。実際の取引を行う前に、必ず動作検証とリスク管理を行ってください。必要であれば、README に含めたい追加情報（外部APIの設定例、サンプル戦略、CI の設定など）を教えてください。